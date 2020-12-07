import numpy as np
import sys
import pandas as pd

from googleapiclient import discovery
from pathlib import PurePath, Path
from youtube_transcript_api import YouTubeTranscriptApi

import config, utils

YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
YOUTUBE = discovery.build(
    YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=config.DEVELOPER_KEY
)

RESULTS_PER_PAGE = 50  # 1-50 as per Google's rules.
MAX_SIZE = 5000

def look_up_resources(pages, requested_items):
    return_dict = {}
    for resource, loc in requested_items.items():
        if len(loc) == 1 or type(loc) == str:
            return_dict[resource] = [
                items[loc] for content in pages for items in content["items"]
            ]
        else:
            nested_resources = []
            for content in pages:
                for items in content["items"]:
                    for i in range(len(loc)):
                        if i < len(loc) - 1:  # stop just before last nested item
                            items = items[loc[i]]
                        else:
                            nested_resources.append(items[loc[i]])
            return_dict[resource] = nested_resources
    return return_dict


def request_from_youtube(
    request_func,
    requested_items,
    root_resource_id,
    file_path,
    file_name,
    save_interval=10,
    only_first_page=False,
):

    i = 0
    pages = []
    next_page_token = None
    while True:
        resource_pages = request_func(root_resource_id, next_page_token).execute()

        if only_first_page:
            resources = look_up_resources([resource_pages], requested_items)
            return pd.DataFrame(resources)

        if resource_pages["pageInfo"]["totalResults"] > MAX_SIZE:
            print("Too many resources. Edit MAX_SIZE to a higher value.")
            sys.exit()

        pages.append(resource_pages)

        if "nextPageToken" in resource_pages:
            next_page_token = resource_pages["nextPageToken"]
            i += 1

            if i % save_interval == 0:
                resources = look_up_resources(pages, requested_items)
                resources_df = pd.DataFrame(resources)
                utils.save_and_rem_files(
                    resources_df, file_path, file_name, i, save_interval
                )

        else:
            resources = look_up_resources(pages, requested_items)
            resources_df = pd.DataFrame(resources)

            utils.save_and_rem_files(
                resources_df, file_path, file_name, i, save_interval, end=True
            )
            break

    return resources_df


def request_channel_ids(channel_name, file_path, file_name):
    def channel_search_func(channel_name, next_page_token):
        return YOUTUBE.search().list(
            part="snippet",
            q=channel_name,
            type="channel",
            fields="items(id(channelId))",
        )

    requested_channel_item = {"channel_ids": ["id", "channelId"]}

    channel_df = request_from_youtube(
        channel_search_func,
        requested_channel_item,
        channel_name,
        file_path,
        file_name,
        save_interval=np.inf,
        only_first_page=True,
    )
    utils.save_and_rem_files(channel_df, file_path, file_name, end=True)

    return channel_df


def request_playlist_ids(channel_id, file_path, file_name, **kwargs):
    save_interval = kwargs["save_interval"]

    def playlist_request_func(channel_id, next_page_token):
        return YOUTUBE.playlists().list(
            part="id,snippet",
            channelId=channel_id,  #   config.CHANNEL_ID, #change to config
            maxResults=RESULTS_PER_PAGE,
            pageToken=next_page_token,
            fields="nextPageToken,pageInfo,items(id),items(snippet(title))",
        )

    requested_playlist_items = {
        "playlist_ids": "id",
        "playlist_titles": ["snippet", "title"],
    }
    playlist_df = request_from_youtube(
        playlist_request_func,
        requested_playlist_items,
        channel_id,
        file_path,
        file_name,
        save_interval,
    )
    return playlist_df


def request_video_ids(playlist_ids, file_path, file_name, **kwargs):
    channel_id, save_interval = kwargs["channel_id"], kwargs["save_interval"]

    def video_request_func(playlist_id, next_page_token):
        return YOUTUBE.playlistItems().list(
            part="snippet",
            maxResults=RESULTS_PER_PAGE,
            playlistId=playlist_id,
            pageToken=next_page_token,
            fields="nextPageToken,pageInfo,items(snippet(title)),items(snippet(resourceId(videoId)))",
        )

    requested_video_items = {
        "video_ids": ["snippet", "resourceId", "videoId"],
        "video_titles": ["snippet", "title"],
    }

    all_videos_df = pd.DataFrame({})

    i = 0
    for playlist_id in playlist_ids:
        videos_df = request_from_youtube(
            video_request_func, requested_video_items, playlist_id, file_path, file_name
        )
        videos_df["playlist_ids"] = [playlist_id] * len(videos_df)
        all_videos_df = pd.concat([all_videos_df, videos_df], ignore_index=True)

        i += 1

        if i % save_interval == 0:
            utils.save_and_rem_files(
                all_videos_df, file_path, file_name, i, save_interval
            )

    all_videos_df.set_index("video_ids", inplace=True)
    all_videos_df = all_videos_df[~all_videos_df.index.duplicated(keep="first")]
    all_videos_df["channel_ids"] = [channel_id] * len(all_videos_df)

    utils.save_and_rem_files(
        all_videos_df, file_path, file_name, i, save_interval, end=True
    )

    return all_videos_df


def request_raw_transcript(videos_df, file_path, file_name, **kwargs):
    save_interval = kwargs["save_interval"]
    lang = kwargs["lang"]

    autogen = []
    manual = []
    passing_video_ids = []

    video_ids = videos_df.index.tolist()

    i = 0
    for video_id in video_ids:
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            transcript_auto = transcript_list.find_generated_transcript([lang])
            transcript_manual = transcript_list.find_manually_created_transcript([lang])
        except ValueError:
            if config.PRINT_TRANSCRIPT_API_ERR:
                print("Transcript not found, and/or:", sys.exc_info()[0])
            continue
        except KeyboardInterrupt:
            raise KeyboardInterrupt
        except Exception:
            if config.PRINT_TRANSCRIPT_API_ERR:
                print("Unexpected error:", sys.exc_info()[0])
            continue

        autogen.append(transcript_auto.fetch())
        manual.append(transcript_manual.fetch())
        passing_video_ids.append((video_id))

        i += 1

        if (i % save_interval == 0) and i > 0:
            intermediate_transcripts_df = pd.DataFrame(
                {"video_ids": passing_video_ids, "autogen": autogen, "manual": manual}
            )
            utils.save_and_rem_files(
                intermediate_transcripts_df, file_path, file_name, i, save_interval
            )

    raw_transcripts_df = pd.DataFrame(
        {"video_ids": passing_video_ids, "autogen": autogen, "manual": manual}
    )

    raw_video_transcripts_df = videos_df.join(
        raw_transcripts_df.set_index("video_ids"), how="inner"
    )

    utils.save_and_rem_files(
        raw_video_transcripts_df, file_path, file_name, i, save_interval, end=True
    )

    return raw_video_transcripts_df


def get_channel_ids(channel_name, file_path, file_name):
    channels = utils.open_file_or_create(
        request_channel_ids,
        channel_name,
        file_path,
        file_name,
    )
    return channels


def get_playlist_ids(channel_id, file_path, file_name, save_interval):
    playlists = utils.open_file_or_create(
        request_playlist_ids,
        channel_id,
        file_path,
        file_name,
        save_interval=save_interval,
    )
    return playlists


def get_video_ids(playlist_ids, file_path, file_name, channel_id, save_interval):
    video_ids = utils.open_file_or_create(
        request_video_ids,
        playlist_ids,
        file_path,
        file_name,
        channel_id=channel_id,
        save_interval=save_interval,
    )
    return video_ids


def get_raw_transcripts(video_ids, file_path, file_name, save_interval, lang):
    transcripts = utils.open_file_or_create(
        request_raw_transcript,
        video_ids,
        file_path,
        file_name,
        save_interval=save_interval,
        lang=lang,
    )
    return transcripts


def get_transcripts(channel_name, file_path, file_name, save_interval, lang):

    channel_ids_df = get_channel_ids(channel_name, config.CHANNEL_PATH, file_name)
    if config.GET_CHANNEL_IDS_ONLY:
        return
    channel_id = channel_ids_df["channel_ids"].tolist()[0]
    full_filename = str(PurePath(config.CHANNEL_PATH, f"{file_name}.json"))
    input(
        f"""
        If below requested channel is correct:
        https://www.youtube.com/channel/{channel_id}
        please hit [Enter]/
        
        Else [ctrl+c] script and check for other `channel_id` options in:
        {full_filename}
        """
    )

    playlist_ids_df = get_playlist_ids(
        channel_id, config.PLAYLIST_PATH, file_name, save_interval
    )
    if config.GET_PLAYLIST_IDS_ONLY:
        return
    playlist_ids = list(set(playlist_ids_df["playlist_ids"].tolist()))

    videos_df = get_video_ids(
        playlist_ids, config.VIDEO_PATH, file_name, channel_id, save_interval
    )
    if config.GET_VIDEO_IDS_ONLY:
        return

    raw_transcripts_df = get_raw_transcripts(
        videos_df,
        config.RAW_TRANSCRIPT_PATH,
        file_name,
        config.TRANSCRIPT_SAVE_INTERVAL,
        lang,
    )
    if len(raw_transcripts_df.video_titles) == 0:
        sys.exit("No manually generated transcripts on this channel")
    return raw_transcripts_df


if __name__ == "__main__":
    lang = config.LANGUAGE
    file_path = config.DATASET_PATH

    channel_name = config.CHANNEL_NAME
    file_name = "_".join(channel_name.split())

    raw_transcripts = get_transcripts(
        channel_name, file_path, file_name, config.SAVE_INTERVAL, lang
    )
