
## Install

In order to use, you need a YouTube API key and pip install the following:
```
pip install pandas
pip install youtube_transcript_api
pip install google-api-python-client
```
You can get the YouTube API key from [here](https://developers.google.com/youtube/v3/getting-started), and then use it to populate `DEVELOPER_KEY` in config.py

## Running the main script
To request transcripts from a youtube channel, populate `CHANNEL_NAME` in config.py, and run `python prepare_data.py`

The script will do a search for this channel name and come back with a list of potential channel_ids, suggesting the top-most. Please click on weblink to confirm that you want to proceed with this channel. Note that all data return from calls to the YouTube API, both directly via the [`googleapiclient`](https://developers.google.com/youtube/v3/quickstart/python) and indirectly via [`youtube_transcript_api`](https://pypi.org/project/youtube-transcript-api/) are backed up incrementally to reduce the likelihood that you have to re-request the same data and risk hitting your daily request limit (but you still don't want to waste a bunch of time on the wrong channel).


## Output
 The final result of running `prepare_data.py` is a panda's DataFrame saved in json that contains transcripts and metadata for any video on that channel that has (in the requested language):
- an 'auto-generated' transcript and 
- a 'manually corrected' transcript 


The differences between these two transcripts will be labeled in a way that is non-destructive to the data, and hopefully flexible enough to be repurposed into more useful labels.

For example the tokens that are mutually different between the two transcripts (rather than a one-sided insertion) can be labeled `1` with all other tokens as `0`, and then trained on a token-level classification task to recognize such 'errors' in auto-generated transcripts. Subsequently, the `1`'s on these tokens can be replaced with a `<MASK>` and trained in a language modeling task, where the 'correct' token for the masked word could come from the 'manually corrected' transcript, rather than the auto-generated transcript. Here the goal is for a language model to learn to fill in a suitable alternative word, when an incorrect word is masked out of a caption.

See the notebook `checkout_data_and_new_label_creation.ipynb` for more details on the dataset and how to initially prepare it for such a training task.