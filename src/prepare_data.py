from pathlib import PurePath
from difflib import Differ

import config
import utils
import request_data


AUTOGEN_UNIQUE = "-"
MANUAL_UNIQUE = "+"


def extract_text(transcript):
    try:
        last_line = transcript[-1]["start"]
        text = []
        for line in transcript:

            if line["start"] <= last_line:
                text.append(line["text"])
            else:
                break

        return " ".join(text)
    except IndexError:
        return "extract_text_error"


def generate_diff(transcript_texts):
    ## from https://docs.python.org/3/library/difflib.html#difflib.Differ
    #################### d.compare symbols ######################
    # '- ' # line unique to sequence 1
    # '+ ' # line unique to sequence 2
    # '  ' # line common to both sequences
    # '? ' # line not present in either input sequence
    # note: symbol is at index 0, string in starts at index 2
    #############################################################
    symbol_idx = 0
    str_start_idx = 2
    autogen = transcript_texts["autogen_text"].split()
    manual = transcript_texts["manual_text"].split()

    d = Differ()

    comp = list(d.compare(autogen, manual))
    # ignoring symbol for 'line not present in either input sequence'
    comp = [element for element in comp if not element.startswith("?")]

    index = 0
    element = comp[index]

    diff_cache = {AUTOGEN_UNIQUE: [], MANUAL_UNIQUE: []}
    diffs = []

    while index < len(comp) - 1:
        if element.startswith((AUTOGEN_UNIQUE, MANUAL_UNIQUE)):
            while element.startswith((AUTOGEN_UNIQUE, MANUAL_UNIQUE)):
                diff_cache[element[symbol_idx]].append(element[str_start_idx:])
                try:
                    index += 1
                    element = comp[index]
                except IndexError:
                    break

            diffs.append(diff_cache)
            diff_cache = {AUTOGEN_UNIQUE: [], MANUAL_UNIQUE: []}

        else:
            diffs.append(element[str_start_idx:])
            try:
                index += 1
                element = comp[index]
            except IndexError:
                break
    return diffs


def label_diff_targets(transcript):

    common_to_both_seq = []
    is_autogen_unique = []
    is_manual_unique = []
    autogen_seq = []
    manual_seq = []
    manual_addl_rep = []

    for tokens in transcript["diffs"]:
        if type(tokens) == dict:

            if len(tokens[AUTOGEN_UNIQUE]) > 0 and len(tokens[MANUAL_UNIQUE]) > 0:
                len_to_extend = len(
                    tokens[AUTOGEN_UNIQUE]
                )  # length of the neg sequence will be used as default len
                common_to_both_seq.extend([""] * len_to_extend)
                is_autogen_unique.extend([config.BOTH_DIFFER] * len_to_extend)
                is_manual_unique.extend([config.BOTH_DIFFER] * len_to_extend)
                autogen_seq.extend(tokens[AUTOGEN_UNIQUE])
                manual_seq.extend(
                    [" ".join(tokens[MANUAL_UNIQUE])] * len_to_extend
                )  # additional repetitions of a token string added to match `autogen_seq` len
                manual_addl_rep.extend([len_to_extend - 1] * len_to_extend)

            elif len(tokens[AUTOGEN_UNIQUE]) > 0:
                len_to_extend = len(tokens[AUTOGEN_UNIQUE])
                common_to_both_seq.extend([""] * len_to_extend)
                is_autogen_unique.extend([config.AUTOGEN_INSERT] * len_to_extend)
                is_manual_unique.extend([config.AUTOGEN_INSERT] * len_to_extend)
                autogen_seq.extend(tokens[AUTOGEN_UNIQUE])
                manual_seq.extend([""] * len_to_extend)
                manual_addl_rep.extend([0] * len_to_extend)

            elif len(tokens[MANUAL_UNIQUE]) > 0:
                # Append only single element, (of joined tokens if necessary)
                # because we set len based on AUTOGEN_UNIQUE
                common_to_both_seq.append("")
                is_autogen_unique.append(config.MANUAL_INSERT)
                is_manual_unique.append(config.MANUAL_INSERT)
                autogen_seq.append("")
                manual_seq.append(" ".join(tokens[MANUAL_UNIQUE]))
                manual_addl_rep.append(0)

        else:
            common_to_both_seq.append(tokens)
            is_autogen_unique.append(config.BOTH_AGREE)
            is_manual_unique.append(config.BOTH_AGREE)
            autogen_seq.append("")
            manual_seq.append("")
            manual_addl_rep.append(0)

    transcript["common_to_both_seq"] = common_to_both_seq
    transcript["is_autogen_unique"] = is_autogen_unique
    transcript["is_manual_unique"] = is_manual_unique
    transcript["autogen_seq"] = autogen_seq
    transcript["manual_seq"] = manual_seq
    transcript["manual_addl_rep"] = manual_addl_rep

    return transcript


def prepare_labeled_transcripts(
    raw_transcripts_df,
    file_path,
    file_name,
):
    transcripts = raw_transcripts_df

    transcripts["autogen_text"] = transcripts["autogen"].apply(extract_text)
    malformed = transcripts["autogen_text"] == "extract_text_error"
    transcripts.drop(index=transcripts[malformed].index, inplace=True)

    transcripts["manual_text"] = transcripts["manual"].apply(extract_text)
    malformed = transcripts["manual_text"] == "extract_text_error"
    transcripts.drop(index=transcripts[malformed].index, inplace=True)

    transcripts["diffs"] = transcripts[["autogen_text", "manual_text"]].apply(
        generate_diff, axis=1
    )
    transcripts = transcripts.apply(label_diff_targets, axis=1)

    transcripts.to_json(str(PurePath(file_path, f"{file_name}.json")))
    return transcripts


def get_video_transcripts(channel_name, file_path, file_name, save_interval, lang):
    raw_transcripts_df = utils.open_file_or_create(
        request_data.get_transcripts,
        channel_name,
        file_path,
        file_name,
        save_interval=save_interval,
        lang=lang,
    )
    return raw_transcripts_df


def get_labeled_transcripts(raw_transcripts_df, file_path, file_name):
    labeled_transcripts_df = utils.open_file_or_create(
        prepare_labeled_transcripts,
        raw_transcripts_df,
        file_path,
        file_name,
    )
    return labeled_transcripts_df


if __name__ == "__main__":
    lang = config.LANGUAGE

    channel_name = config.CHANNEL_NAME
    file_name = "_".join(channel_name.split())

    raw_transcripts_df = get_video_transcripts(
        channel_name,
        config.RAW_TRANSCRIPT_PATH,
        file_name,
        config.TRANSCRIPT_SAVE_INTERVAL,
        lang,
    )

    labeled_transcripts_df = get_labeled_transcripts(
        raw_transcripts_df, config.LABELED_TRANSCRIPT_PATH, file_name
    )
