import argparse
import re
import nltk

from nltk.corpus import stopwords
from nltk.stem.porter import PorterStemmer

from pathlib import PurePath
from string import punctuation

import config
import utils
import prepare_data

nltk.download("stopwords")


def get_autogen_reconstruct(example):
    autogen_reconstruct = []
    labels = example.is_autogen_unique
    for idx, label in enumerate(labels):
        if label == config.BOTH_AGREE:
            autogen_reconstruct.append(example.common_to_both_seq[idx])
        if label == config.AUTOGEN_INSERT or label == config.BOTH_DIFFER:
            autogen_reconstruct.append(example.autogen_seq[idx])
        if label == config.MANUAL_INSERT:
            autogen_reconstruct.append("")
    return autogen_reconstruct


def get_manual_reconstruct(example):
    manual_reconstruct = []
    labels = example.is_manual_unique
    i = 0
    while i < len(labels):
        if labels[i] == config.BOTH_AGREE:
            manual_reconstruct.append(example.common_to_both_seq[i])
        elif labels[i] == config.MANUAL_INSERT:
            manual_reconstruct.extend(example.manual_seq[i].split())
        elif labels[i] == config.BOTH_DIFFER:
            manual_reconstruct.extend(example.manual_seq[i].split())
            i += example.manual_addl_rep[i]
        i += 1
    return manual_reconstruct


def add_simple_single_token_diff_labels(t, tokenizer, stemmer, en_stopwords):

    default_seq = get_autogen_reconstruct(t)
    correction_seq = [""] * len(t.autogen_seq)
    new_labels = [0] * len(t.autogen_seq)

    for idx in range(len(t.autogen_seq)):
        # Ingore if not a mutual token difference
        if t.is_autogen_unique[idx] == config.BOTH_DIFFER:

            auto_token = t.autogen_seq[idx]
            # num reps == num additional reps +1
            n_reps = t.manual_addl_rep[idx] + 1  
            # Is same number of tokens different in both sequences
            if len(t.manual_seq[idx].split()) == n_reps:
                # If any address addl tokens, address in next iters
                t.manual_seq[idx : idx + n_reps] = t.manual_seq[idx].split()
                t.manual_addl_rep[idx : idx + n_reps] = [0] * n_reps
            else:
                continue  # Only labeling same len token diffs
            man_token = t.manual_seq[idx]

            if auto_token.lower() == man_token.lower():
                new_labels[idx] = config.CASE_DIFF

            elif auto_token.strip(punctuation) == man_token.strip(punctuation):
                new_labels[idx] = config.PUNCUATION_DIFF

            elif auto_token.lower().strip(punctuation) == man_token.lower().strip(
                punctuation
            ):
                new_labels[idx] = config.CASE_AND_PUNCUATION_DIFF

            elif stemmer.stem(auto_token.lower()) == stemmer.stem(man_token.lower()):
                new_labels[idx] = config.STEM_BASED_DIFF

            #  E.g. `2` <-> `two` is a common diff
            elif re.match("\d+", man_token) or re.match("\d+", auto_token):
                new_labels[idx] = config.DIGIT_DIFF

            elif "".join(tokenizer.tokenize(auto_token)).lower().strip(
                punctuation
            ) == "".join(tokenizer.tokenize(man_token)).lower().strip(punctuation):
                new_labels[idx] = config.INTRAWORD_PUNC_DIFF

            else:
                new_labels[idx] = config.UNKNOWN_TYPE_DIFF

            correction_seq[idx] = man_token

    t["is_single_simple_diff"] = new_labels
    t["default_seq"] = default_seq
    t["correction_seq"] = correction_seq
    return t


def prepare_postproc_transcripts(labeled_transcripts_df, file_path, file_name):

    tokenizer = nltk.RegexpTokenizer(r"\w+")
    stemmer = PorterStemmer()
    en_stopwords = stopwords.words("english")

    transcripts = labeled_transcripts_df.apply(
        add_simple_single_token_diff_labels,
        axis=1,
        args=(tokenizer, stemmer, en_stopwords),
    )

    if config.USE_ONLY_POSTPROC_LABELS:
        transcripts = transcripts[
            [
                "video_titles",
                "playlist_ids",
                "channel_ids",
                "is_single_simple_diff",
                "default_seq",
                "correction_seq",
            ]
        ]
    if not config.USE_VIDEO_ID_AS_IDX:
        transcripts = transcripts.reset_index().rename(columns={"index": "video_ids"})

    transcripts.to_json(str(PurePath(file_path, f"{file_name}.json")), orient="records")
    return transcripts


def get_labeled_transcripts(channel_name, file_path, file_name):
    labeled_transcripts_df = utils.open_file_or_create(
        prepare_data.prepare_labeled_transcripts,
        raw_transcripts_df,
        file_path,
        file_name,
    )
    return labeled_transcripts_df


def get_postproc_transcripts(raw_transcripts_df, file_path, file_name):
    postproc_transcripts_df = utils.open_file_or_create(
        prepare_postproc_transcripts,
        labeled_transcripts_df,
        file_path,
        file_name,
    )
    return postproc_transcripts_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-c", "--channel", action="store", default=None, help="YouTube channel name"
    )

    args = parser.parse_args()

    if args.channel == None:
        channel_name = config.CHANNEL_NAME
    else:
        channel_name = args.channel

    file_name = "_".join(channel_name.split())

    raw_transcripts_df = prepare_data.get_video_transcripts(
        channel_name,
        config.RAW_TRANSCRIPT_PATH,
        file_name,
        config.TRANSCRIPT_SAVE_INTERVAL,
        config.LANGUAGE,
    )

    labeled_transcripts_df = get_labeled_transcripts(
        raw_transcripts_df, config.LABELED_TRANSCRIPT_PATH, file_name
    )

    postproc_transcripts_df = get_postproc_transcripts(
        labeled_transcripts_df, config.POSTPROC_TRANSCRIPT_PATH, file_name
    )
