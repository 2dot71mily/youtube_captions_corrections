from pathlib import PurePath

### Prefs ###
LANGUAGE = "en"
CHANNEL_NAME = "Jeremy Howard"

GET_CHANNEL_IDS_ONLY = False
GET_PLAYLIST_IDS_ONLY = False
GET_VIDEO_IDS_ONLY = False

SAVE_INTERVAL = 100
TRANSCRIPT_SAVE_INTERVAL = SAVE_INTERVAL

PRINT_TRANSCRIPT_API_ERR = False
DEVELOPER_KEY = "<API_KEY_HERE>"

### Paths ###
PATH_ROOT = "/Users/emcmilin/youtube_captions_corrections"
DATASET_PATH = PurePath(PATH_ROOT, "data")

CHANNEL_PATH = PurePath(DATASET_PATH, "channels")
PLAYLIST_PATH = PurePath(DATASET_PATH, "playlists")
VIDEO_PATH = PurePath(DATASET_PATH, "videos")
TRANSCRIPTS_PATH = PurePath(DATASET_PATH, "transcripts")

LANG_PATH = PurePath(TRANSCRIPTS_PATH, LANGUAGE)
RAW_TRANSCRIPT_PATH = PurePath(LANG_PATH, "raw_transcripts")
LABELED_TRANSCRIPT_PATH = PurePath(LANG_PATH, "labeled_transcripts")
COMBINED_LABELED_PATH =  PurePath(LABELED_TRANSCRIPT_PATH, "combined")
COMBINED_LABELED_FILENAME = "all_channels_transcripts"