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
from config import UploadCFG

# TODO!
# global config check what is in it
# UploadCFG: subtitle3

# Set up logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)


class Uploader:
    def __init__(self):
        self.config = UploadCFG()

        self.subtitles_path = None

    def _generate_subtitles(
        self, video_path: str, beat_info: Dict, yt_title: str
    ) -> Optional[str]:
        logging.debug(f"Generating subtitles for {video_path}")

        try:
            duration = FFcomms.get_duration(video_path)
            subtitles = []

            for i in range(0, int(duration), 30):
                subtitles.extend(
                    [
                        srt.Subtitle(
                            index=i * 3 + 1,
                            start=timedelta(seconds=i),
                            end=timedelta(seconds=i + 10),
                            content=yt_title,
                        ),
                        srt.Subtitle(
                            index=i * 3 + 2,
                            start=timedelta(seconds=i + 10),
                            end=timedelta(seconds=i + 20),
                            content=f"{beat_info['key']} - {beat_info['tempo']} BPM",
                        ),
                        srt.Subtitle(
                            index=i * 3 + 3,
                            start=timedelta(seconds=i + 20),
                            end=timedelta(seconds=i + 30),
                            content=self.config.subtitle3,
                        ),
                    ]
                )

            srt_content = srt.compose(subtitles)
            srt_path = video_path.rsplit(".", 1)[0] + ".srt"
            with open(srt_path, "w") as f:
                f.write(srt_content)
            logging.info(f"Subtitles generated successfully: {srt_path}")
            return srt_path

        except Exception as e:
            logging.exception(f"Error generating subtitles: {str(e)}")
            return None

    def generate_description(
        beat_info: Dict, channel_config: Dict, global_config: Dict, yt_title: str
    ) -> str:
        description_parts = [
            f"💰 Purchase This Beat (Buy 2 Get 2 Free) | {beat_info.get('purchase_link', '')} \n\n",
            f"BPM: {beat_info.get('tempo', '')}\n",
            f"KEY: {beat_info.get('key', '')}\n\n",
            "Instagram: https://www.instagram.com/matejcikbeats\n",
            "Email: matejcikbeats@gmail.com\n",
            "Beat Store: https://matejcikbeats.infinity.airbit.com/\n",
            f"Prod. {beat_info.get('collaborators', '')}\n\n",
            "This instrumental is free to use for non-profit use. If you have any questions, please contact me.\n",
            "A license must be purchased to use for profit (Streaming Services, music videos, etc.)\n",
            "Must Credit: (prod. matejcikbeats)\n\n",
            "TAGS (IGNORE):\n\n",
            f"{yt_title.upper()}\n\n",
            f"{channel_config.get('Gpt', '')}\n\n",
            "Some other ways I would describe this beat:\n",
            channel_config.get("Tags2", ""),
        ]

        # Join all parts without any additional newlines
        return "".join(part for part in description_parts if part is not None)

    def generate_youtube_data(
        channel_config: Dict,
        global_config: Dict,
        beat_info: Dict,
        video_link: str,
        subtitles_link: str,
        thumbnail_link: str,
    ) -> Dict:
        config = {**global_config, **channel_config}

        if config.get("Title_suffix", "") != None:
            yt_title = f'{config.get("Title", "")} "{beat_info["name"]}" {config.get("Title_suffix", "")}'
        else:
            yt_title = f'{config.get("Title", "")} "{beat_info["name"]}"'

        description = generate_description(
            beat_info, channel_config, global_config, yt_title
        )

        return {
            "Text": description,
            "Year": None,
            "Month (1 to 12)": None,
            "Date": None,
            "Hour (From 0 to 23)": None,
            "Minutes": None,
            "Queue Schedule": "QLAST",
            "Post Type": "VIDEO",
            "Video Title": yt_title.upper(),
            "Video URL": video_link,
            "Thumbnail URL": thumbnail_link,
            "Subtitles URL": subtitles_link,
            "Subtitles Language": "en",
            "Subtitles Auto-Sync": "No",
            "Privacy Status": "PUBLIC",
            "Category": "10",
            "Playlist": config.get("Playlist"),
            "Tags": config.get("Tags"),
            "License": "YOUTUBE",
            "Embeddable": "Yes",
            "Notify Subscribers": "Yes",
            "Made For Kids": "No",
        }

    def extract_beat_name(self, folder_name: str) -> str:
        try:
            beat = BeatManager.parse_filename(folder_name)
            return beat.name.lower()
        except Exception as e:
            logging.error(f"Error parsing folder name '{folder_name}': {str(e)}")
            return ""

    def find_video_file(self, folder_path: str) -> Optional[str]:
        video_extensions = [".mp4", ".mov", ".avi", ".wmv"]
        for file in os.listdir(folder_path):
            if any(file.lower().endswith(ext) for ext in video_extensions):
                return os.path.join(folder_path, file)
        return None

    def find_thumbnail_file(self, folder_path: str) -> Optional[str]:
        for file in os.listdir(folder_path):
            if file.lower().endswith("_thumbnail.jpg"):
                return os.path.join(folder_path, file)
        return None

    def upload_to_dropbox(
        self, file_path: str, dropbox_folder: str, dropbox_instance
    ) -> Optional[str]:
        file_generator = process_files_with_dropbox(
            os.path.dirname(file_path), dropbox_folder, dropbox_instance
        )
        upload_result = next(file_generator, (None, None))
        return upload_result[1]  # Return the download link

    def extract_bpm_from_folder(self, folder_name: str) -> Optional[int]:
        parts = folder_name.split()
        for part in parts:
            if part.isdigit():
                return int(part)
        logging.warning(f"Could not extract BPM from folder name: {folder_name}")
        return None

    # Rework this
    def get_dropbox_variable(self, config):
        dropbox_version = config.get(
            "Dropbox", "dropbox2"
        )  # Default to 'dropbox2' if not specified
        if dropbox_version not in ["dropbox", "dropbox2", "dropbox3"]:
            raise ValueError(f"Invalid dropbox version: {dropbox_version}")

        return getattr(Publisher, dropbox_version)

    def process_folder(
        self,
        folder_path: str,
        channel_name: str,
        channel_config: Dict,
        global_config: Dict,
        beat_manager: BeatManager,
    ) -> Optional[Dict]:
        logging.info(f"Processing folder: {folder_path}")
        youtube_data = None

        try:
            folder_name = os.path.basename(folder_path)
            beatname = extract_beat_name(folder_name)
            logging.debug(f"Extracted beat name: '{beatname}'")

            if not beatname:
                logging.warning(
                    f"Could not extract a valid beat name from folder '{folder_name}'. Skipping this folder."
                )
                return None

            beat_results = beat_manager.search_beats(beatname, search_by="name")
            logging.debug(f"Beat search results: {beat_results}")

            if not beat_results:
                logging.warning(
                    f"Beat '{beatname}' not found in the database. Skipping this folder."
                )
                return None

            folder_bpm = extract_bpm_from_folder(folder_name)
            if folder_bpm is None:
                logging.warning(
                    f"Could not extract BPM from folder '{folder_name}'. Skipping this folder."
                )
                return None

            matching_beat = next(
                (
                    beat
                    for beat in beat_results
                    if len(beat) >= 5 and beat[4] == folder_bpm
                ),
                None,
            )

            if not matching_beat:
                logging.warning(
                    f"No beat found with name '{beatname}' and BPM {folder_bpm}. Skipping this folder."
                )
                return None

            if len(matching_beat) < 9:
                logging.warning(
                    f"Incomplete beat information for '{beatname}'. Skipping this folder."
                )
                return None

            beat_info = {
                "name": matching_beat[1],
                "collaborators": matching_beat[2],
                "key": matching_beat[3],
                "tempo": matching_beat[4],
                "purchase_link": matching_beat[8],
            }

            logging.debug(f"Beat info: {beat_info}")

            if not beat_info["purchase_link"] or beat_info["purchase_link"] == "None":
                logging.warning(
                    f"No purchase link found for beat '{beatname}' in the database."
                )
                purchase_link = input(f"Enter purchase link for beat '{beatname}': ")
                beat_manager.update_link(matching_beat[0], purchase_link)
                beat_info["purchase_link"] = purchase_link
                logging.info(
                    f"Updated purchase link for beat '{beatname}': {purchase_link}"
                )

            if not beat_info["purchase_link"]:
                logging.warning(
                    f"No purchase link provided for beat '{beatname}'. Skipping this folder."
                )
                return None

            video_file = find_video_file(folder_path)
            if not video_file:
                logging.warning(
                    f"No video file found in folder '{folder_path}'. Skipping this folder."
                )
                return None

            dropbox_token = get_dropbox_variable(channel_config)
            dropbox_folder_name = "TypeBeat"
            uploaded_files = list(
                process_files_with_dropbox(
                    folder_path, dropbox_folder_name, dropbox_token
                )
            )

            video_link = next(
                (
                    link
                    for name, link in uploaded_files
                    if name.lower() == os.path.basename(video_file).lower()
                ),
                None,
            )
            if not video_link:
                logging.warning(
                    f"Failed to upload video for '{beatname}' to Dropbox. Skipping this folder."
                )
                return None

            yt_title = f"{channel_config.get('Title', '')} \"{beat_info['name']}\""
            srt_path = generate_subtitles(video_file, beat_info, yt_title)
            if not srt_path:
                logging.warning(
                    f"Failed to generate SRT file for '{beatname}'. Skipping this folder."
                )
                return None

            subtitles_link = None
            max_retries = 3
            retry_delay = 5  # seconds
            for attempt in range(max_retries):
                try:
                    subtitles_link = upload_to_dropbox(
                        srt_path, dropbox_folder_name, dropbox_token
                    )
                    if subtitles_link:
                        break
                    else:
                        raise Exception("SRT upload failed")
                except Exception as e:
                    if attempt < max_retries - 1:
                        logging.warning(
                            f"Attempt {attempt + 1} failed to upload SRT file for '{beatname}'. Retrying in {retry_delay} seconds..."
                        )
                        time.sleep(retry_delay)
                    else:
                        logging.error(
                            f"Failed to upload SRT file for '{beatname}' after {max_retries} attempts. Skipping this folder."
                        )
                        return None

            if not subtitles_link:
                logging.warning(
                    f"Failed to upload SRT file for '{beatname}' to Dropbox. Skipping this folder."
                )
                return None

            thumbnail_file = find_thumbnail_file(folder_path)
            if thumbnail_file:
                thumbnail_link = next(
                    (
                        link
                        for name, link in uploaded_files
                        if name.lower() == os.path.basename(thumbnail_file).lower()
                    ),
                    None,
                )
                if not thumbnail_link:
                    logging.warning(
                        f"Failed to upload thumbnail for '{beatname}' to Dropbox. Using default thumbnail."
                    )
                    thumbnail_link = channel_config.get("default_thumbnail_url", None)
            else:
                logging.warning(
                    f"Thumbnail for '{beatname}' not found. Using default thumbnail."
                )
                thumbnail_link = channel_config.get("default_thumbnail_url", None)

            youtube_data = generate_youtube_data(
                channel_config,
                global_config,
                beat_info,
                video_link,
                subtitles_link,
                thumbnail_link,
            )

            logging.info(f"Folder '{folder_path}' processed successfully.")
            return youtube_data

        except Exception as e:
            logging.exception(f"Error processing folder '{folder_path}': {str(e)}")
            return None

        finally:
            if youtube_data:
                try:
                    shutil.rmtree(folder_path)
                    logging.info(
                        f"Folder '{folder_path}' has been deleted after successful processing."
                    )

                except Exception as delete_error:
                    logging.error(
                        f"Failed to delete folder '{folder_path}': {str(delete_error)}"
                    )
            else:
                logging.info(
                    f"Folder '{folder_path}' was not deleted due to processing errors."
                )

    def save_to_csv(data: List[Dict], channel_name: str, script_dir: str):
        logging.debug(f"Attempting to save {len(data)} items to CSV")
        if not data:
            logging.warning("No data to save")
            return

        template_path = os.path.join(
            script_dir, f"{Publisher.resources_path}/Bulk_Uploader_YouTube_Template.csv"
        )

        try:
            with open(
                template_path, "r", newline="", encoding="utf-8"
            ) as template_file:
                csv_reader = csv.DictReader(template_file)
                fieldnames = csv_reader.fieldnames

            current_time = datetime.now()
            output_filename = (
                f"{channel_name}_{current_time.strftime('%Y-%m-%d_%H-%M-%S')}.csv"
            )
            output_path = os.path.join(script_dir, output_filename)

            with open(output_path, "w", newline="", encoding="utf-8") as output_file:
                csv_writer = csv.DictWriter(output_file, fieldnames=fieldnames)
                csv_writer.writeheader()
                for row in data:
                    csv_writer.writerow(row)

            logging.info(f"Data saved to {output_path}")
        except Exception as e:
            logging.error(f"Error saving CSV: {str(e)}")

    def get_valid_folder_path() -> str:
        while True:
            folder_path = input(
                "Enter the root folder path containing the video folders: "
            ).strip("'\"")
            if os.path.exists(folder_path) and os.path.isdir(folder_path):
                return folder_path
            else:
                logging.error(
                    f"The folder '{folder_path}' does not exist or is not a directory. Please try again."
                )

    def main():
        channel_name = input("Enter the YouTube channel name: ")
        channel_config, global_config = get_configs(channel_name)
        if not channel_config or not global_config:
            return

        root_folder = get_valid_folder_path()

        beat_manager = BeatManager(Management.database_path_beats)

        all_youtube_data = []

        for folder_name in os.listdir(root_folder):
            folder_path = os.path.join(root_folder, folder_name)
            if os.path.isdir(folder_path):
                youtube_data = process_folder(
                    folder_path,
                    channel_name,
                    channel_config,
                    global_config,
                    beat_manager,
                )
                if youtube_data:
                    all_youtube_data.append(youtube_data)

        beat_manager.close()

        if all_youtube_data:
            save_to_csv(
                all_youtube_data,
                channel_name,
                os.path.dirname(os.path.abspath(__file__)),
            )
        else:
            logging.warning(
                "No data was processed successfully. No CSV file will be generated."
            )


if __name__ == "__main__":
    main()
