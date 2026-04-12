import os
import csv
import logging
import shutil
from pathlib import Path
from datetime import timedelta, datetime
from typing import Optional

import srt

from dropbox_integration import process_files_with_dropbox
from beat_management import BeatManager
from utils import FFcomms
from config import UploadCFG, ChannelCFG, DBConfig

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)

_CSV_TEMPLATE = (
    Path(__file__).parent / "resources" / "Bulk_Uploader_YouTube_Template.csv"
)


class Video:
    def __init__(
        self,
        video_path: str,
        beat_info: dict,
        upload_cfg: UploadCFG,
        channel_cfg: ChannelCFG,
    ):
        self.video_path = video_path
        self.beat_info = beat_info
        self.upload_cfg = upload_cfg
        self.channel_cfg = channel_cfg

        self.yt_title = self._build_title()
        self.description = self._build_description()
        self.srt_path: Optional[str] = None

    def _build_title(self) -> str:
        suffix = self.channel_cfg.title_suffix
        if suffix:
            return f'{self.channel_cfg.title} "{self.beat_info["name"]}" {suffix}'
        return f'{self.channel_cfg.title} "{self.beat_info["name"]}"'

    def _build_description(self) -> str:
        parts = [
            f"💰 Purchase This Beat (Buy 2 Get 2 Free) | {self.beat_info.get('link', '')}\n\n",
            f"BPM: {self.beat_info.get('tempo', '')}\n",
            f"KEY: {self.beat_info.get('key', '')}\n\n",
            f"Instagram: {self.upload_cfg.ig}\n",
            f"Email: {self.upload_cfg.email}\n",
            f"Beat Store: {self.upload_cfg.store}\n",
            f"Prod. {self.beat_info.get('collaborators', '')}\n\n",
            "This instrumental is free to use for non-profit use. If you have any questions, please contact me.\n",
            "A license must be purchased to use for profit (Streaming Services, music videos, etc.)\n",
            f"Must Credit: (prod. {self.upload_cfg.prodname})\n\n",
            "TAGS (IGNORE):\n\n",
            f"{self.yt_title.upper()}\n\n",
            f"{self.channel_cfg.gpt_tags}\n\n",
        ]
        return "".join(parts)

    def generate_subtitles(self):
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
                        content=self.upload_cfg.subtitle3,
                    ),
                ]
            )

        srt_content = srt.compose(subtitles)
        self.srt_path = self.video_path.rsplit(".", 1)[0] + ".srt"

        with open(self.srt_path, "w") as f:
            f.write(srt_content)

        logging.info(f"Subtitles written to {self.srt_path}")

    def to_csv_row(
        self, video_link: str, subtitles_link: str, thumbnail_link: Optional[str]
    ) -> dict:
        return {
            "Text": self.description,
            "Year": None,
            "Month (1 to 12)": None,
            "Date": None,
            "Hour (From 0 to 23)": None,
            "Minutes": None,
            "Queue Schedule": "QLAST",
            "Post Type": "VIDEO",
            "Video Title": self.yt_title.upper(),
            "Video URL": video_link,
            "Thumbnail URL": thumbnail_link,
            "Subtitles URL": subtitles_link,
            "Subtitles Language": "en",
            "Subtitles Auto-Sync": "No",
            "Privacy Status": "PUBLIC",
            "Category": "10",
            "Playlist": self.channel_cfg.playlist,
            "Tags": self.channel_cfg.tags,
            "License": "YOUTUBE",
            "Embeddable": "Yes",
            "Notify Subscribers": "Yes",
            "Made For Kids": "No",
        }


class Uploader:
    def __init__(self, channel_name: str):
        self.upload_cfg = UploadCFG()
        self.channel_cfg = ChannelCFG(channel_name)
        self.channel_name = channel_name
        self._db_cfg = DBConfig()

    def _find_file(self, folder_path: str, match_fn) -> Optional[str]:
        for file in os.listdir(folder_path):
            if match_fn(file):
                return os.path.join(folder_path, file)
        return None

    def _find_video(self, folder_path: str) -> Optional[str]:
        return self._find_file(
            folder_path, lambda f: f.lower().endswith((".mp4", ".mov", ".avi", ".wmv"))
        )

    def _find_thumbnail(self, folder_path: str) -> Optional[str]:
        return self._find_file(
            folder_path, lambda f: f.lower().endswith("_thumbnail.jpg")
        )

    def process_folder(self, folder_path: str) -> Optional[dict]:
        logging.info(f"Processing folder: {folder_path}")

        folder_name = os.path.basename(folder_path)
        try:
            beat_parsed = BeatManager.parse_filename(folder_name)
            beatname = beat_parsed.name.lower()

        except Exception as e:
            logging.error(f"Error parsing folder name '{folder_name}': {e}")
            return None

        results = self.manager.search_beats(beatname, search_by="name")
        if not results:
            logging.warning(f"No database entry found for '{beatname}'. Skipping.")
            return None

        row = results[0]
        beat_info = {
            "name": row[1],
            "collaborators": row[2],
            "key": row[3],
            "tempo": row[4],
            "link": row[6],
        }

        if not beat_info["link"]:
            logging.warning(f"No purchase link for '{beatname}'. Skipping.")
            return None

        video_file = self._find_video(folder_path)
        if not video_file:
            logging.warning(f"No video file found in '{folder_path}'. Skipping.")
            return None

        video = Video(video_file, beat_info, self.upload_cfg, self.channel_cfg)

        try:
            video.generate_subtitles()
        except Exception as e:
            logging.error(f"Failed to generate subtitles for '{beatname}': {e}")
            return None

        dropbox_folder = "TypeBeat"
        token = self.upload_cfg.dropbox_token
        uploaded = list(process_files_with_dropbox(folder_path, dropbox_folder, token))
        uploaded_map = {name.lower(): link for name, link in uploaded}

        video_link = uploaded_map.get(os.path.basename(video_file).lower())
        if not video_link:
            logging.warning(f"Failed to upload video for '{beatname}'. Skipping.")
            return None

        subtitles_link = uploaded_map.get(os.path.basename(video.srt_path).lower())
        if not subtitles_link:
            logging.warning(f"Failed to upload subtitles for '{beatname}'. Skipping.")
            return None

        thumbnail_file = self._find_thumbnail(folder_path)
        thumbnail_link = (
            uploaded_map.get(os.path.basename(thumbnail_file).lower())
            if thumbnail_file
            else None
        )
        if not thumbnail_link:
            logging.warning(f"No thumbnail uploaded for '{beatname}'.")

        youtube_data = video.to_csv_row(video_link, subtitles_link, thumbnail_link)
        logging.info(f"Folder '{folder_path}' processed successfully.")

        try:
            shutil.rmtree(folder_path)
            logging.info(f"Deleted folder '{folder_path}'.")
        except Exception as e:
            logging.error(f"Failed to delete folder '{folder_path}': {e}")

        return youtube_data

    def process_root(self, root_path: str):
        all_data = []

        for folder_name in os.listdir(root_path):
            folder_path = os.path.join(root_path, folder_name)
            if not os.path.isdir(folder_path):
                continue
            data = self.process_folder(folder_path)
            if data:
                all_data.append(data)

        if all_data:
            self._save_csv(all_data)
        else:
            logging.warning("No folders processed successfully. No CSV generated.")

    def _save_csv(self, data: list[dict]):
        try:
            with open(_CSV_TEMPLATE, "r", newline="", encoding="utf-8") as f:
                fieldnames = csv.DictReader(f).fieldnames

            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            output_path = Path(__file__).parent / f"{self.channel_name}_{timestamp}.csv"

            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)

            logging.info(f"CSV saved to {output_path}")

        except Exception as e:
            logging.error(f"Error saving CSV: {e}")


if __name__ == "__main__":
    channel_name = input("Enter the YouTube channel name: ")
    uploader = Uploader(channel_name)

    root_path = input(
        "Enter the root folder path containing the video folders: "
    ).strip("'\"")
    if not os.path.isdir(root_path):
        logging.error(f"'{root_path}' is not a valid directory.")
    else:
        uploader.process_root(root_path)
