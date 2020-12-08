import pandas as pd
import numpy as np
import re
import nltk
import torch

from nltk.corpus import stopwords
from nltk.stem.porter import PorterStemmer

from pathlib import PurePath
from string import punctuation

import config
import utils
import prepare_data

nltk.download('stopwords')
SIMPLE_SINGLE_DIFF_LABEL = 1

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
            i+=example.manual_addl_rep[i]
        i+=1
    return manual_reconstruct 


def add_simple_single_token_diff_labels(t, tokenizer, stemmer, en_stopwords):
    REP_TARGET = 0 # looking for only a single token differences (no repetitions)
    
    default_seq = get_autogen_reconstruct(t)
    correction_seq = [""]*len(t.autogen_seq)
    new_labels = [0]*len(t.autogen_seq)

    
    for idx in range(len(t.autogen_seq)):
        # Ingore if not a mutual single token difference
        if (
            t.is_autogen_unique[idx] == config.BOTH_DIFFER  
            and t.manual_addl_rep[idx] == REP_TARGET 
            and len(t.manual_seq[idx].split()) == 1   
        ):
            auto_token = t.autogen_seq[idx]
            man_token = t.manual_seq[idx]
            
            if (
                # Ignore if difference only case of puncuation
                auto_token.lower() != man_token.lower()
                and ''.join(tokenizer.tokenize(auto_token)) != ''.join(tokenizer.tokenize(man_token))
                # Ingore if shared stem or are 'uninteresting' stop words
                and stemmer.stem(auto_token) != stemmer.stem(man_token)
                and auto_token.lower() not in en_stopwords 
                and man_token.lower() not in en_stopwords 
                # Ignore digits: e.g. `2` <-> `two` is a common diff
                and not re.match("\d+", man_token)  
                and not re.match("\d+", auto_token)
                # Ignore if intra/inter-word puncuation and case
                and ''.join(tokenizer.tokenize(auto_token)).lower().strip(punctuation) 
                != ''.join(tokenizer.tokenize(man_token)).lower().strip(punctuation) 
            ):
                new_labels[idx] = config.SIMPLE_SINGLE_DIFF_LABEL
                correction_seq[idx] = man_token

    t['is_single_simple_diff'] = new_labels
    t['default_seq'] = default_seq
    t['correction_seq'] = correction_seq
    return t


def prepare_postproc_transcripts(
        labeled_transcripts_df, file_path, file_name
    ): 
    
    tokenizer = nltk.RegexpTokenizer(r"\w+")
    stemmer = PorterStemmer()
    en_stopwords = stopwords.words("english")

    transcripts = labeled_transcripts_df.apply(
            add_simple_single_token_diff_labels, 
            axis=1, 
            args=(tokenizer, stemmer, en_stopwords)
        )

    if config.USE_ONLY_POSTPROC_LABELS:
        transcripts=transcripts[['video_titles', 'playlist_ids', 'channel_ids', 'is_single_simple_diff', 'default_seq', 'correction_seq']] 
        
    transcripts.to_json(str(PurePath(file_path, f"{file_name}.json")))
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

    channel_name = config.CHANNEL_NAME
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
    