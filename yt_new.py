import os
import csv
import time
from typing import Dict, List, Tuple, Optional
import srt
from datetime import timedelta, datetime
import logging
import shutil

from dropbox_integration import process_files_with_dropbox
from beat_management import BeatManager

from utils import FFcomms
from config import UploadCFG, ChannelCFG

# TODO!
# global config check what is in it
# UploadCFG: subtitle3
# ChannelCFG that will replace my currect channel cfg logic. It will be passed from the main because it is repeated.

# Set up logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)


class Video:
    def __init__(
        self, video_path, upload_config: UploadCFG, channel_config: ChannelCFG
    ):
        self.config = UploadCFG()
        self.channelcfg = ChannelCFG()
        self.video_path = video_path

        self.yt_title = None
        self.beat_info = {}

        self.description = []

        self.srt_content = None
        self.srt_path = None

    def _generate_description(self):
        description_parts = [
            f"💰 Purchase This Beat (Buy 2 Get 2 Free) | {self.beat_info.get('purchase_link', '')} \n\n",
            f"BPM: {self.beat_info.get('tempo', '')}\n",
            f"KEY: {self.beat_info.get('key', '')}\n\n",
            f"Instagram: {self.channelcfg.get('ig', '')} \n",
            f"Email: {self.channelcfg.get('ig', '')} \n",
            "Beat Store: https://matejcikbeats.infinity.airbit.com/\n",
            f"Prod. {beat_info.get('collaborators', '')}\n\n",
            "This instrumental is free to use for non-profit use. If you have any questions, please contact me.\n",
            "A license must be purchased to use for profit (Streaming Services, music videos, etc.)\n",
            "Must Credit: (prod. matejcikbeats)\n\n",
            "TAGS (IGNORE):\n\n",
            f"{yt_title.upper()}\n\n",
            f"{channel_config.get('Gpt', '')}\n\n",
        ]

    def _generate_subtitles(self):
        logging.debug(f"Generating subtitles for {self.video_path}")

        duration = FFcomms.get_duration(self.video_path)
        subtitles = []

        for i in range(0, int(duration), 30):
            subtitles.extend(
                [
                    srt.Subtitle(
                        index=i * 3 + 1,
                        start=timedelta(seconds=i),
                        end=timedelta(seconds=i + 10),
                        content=self.yt_title,
                    ),
                    srt.Subtitle(
                        index=i * 3 + 2,
                        start=timedelta(seconds=i + 10),
                        end=timedelta(seconds=i + 20),
                        content=f"{self.beat_info['key']} - {self.beat_info['tempo']} BPM",
                    ),
                    srt.Subtitle(
                        index=i * 3 + 3,
                        start=timedelta(seconds=i + 20),
                        end=timedelta(seconds=i + 30),
                        content=self.config.subtitle3,
                    ),
                ]
            )

        self.srt_content = srt.compose(subtitles)

    def dump_subtitles(self):
        try:
            self.srt_path = self.video_path.rsplit(".", 1)[0] + ".srt"

            with open(self.srt_path, "w") as f:
                f.write(self.srt_content)

            logging.info(f"Subtitles generated successfully: {self.srt_path}")

        except Exception as e:
            logging.exception(f"Error generating subtitles: {str(e)}")
