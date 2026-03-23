from pathlib import Path
import sys
import os
import subprocess
import shutil
import random

from utils import listdir_nohidden, count_files, FFcomms, UserPath
from beat_management import BeatManager
from config import ProcessConfig, DBConfig

# To implement:
# if fails on read config, stop init and run that first
# self.config.artists - reads the config and does the artist list
# self.config.pics_path, vids_path - reads the vid and pic path
# self.config.export_dir - I have no idea what this was, but it was in the config...
# self.config.mp3_dir - for mp3s

# config ffargs!!


class Process:
    def __init__(self):
        self.config = ProcessConfig()
        self.artists = self.config.artists

        self.db_config = DBConfig
        self.manager = BeatManager(self.db_config.db_beats)
        self.ffcomm = FFcomms(self.config.ffargs)

        self.artist_picked = None
        self.pic_path = None
        self.vid_path = None

        self.beatlist = []

    def get_valid_artist(self):
        while True:
            artist = input(f"Choose an artist ({' / '.join(self.artists)}): ")
            if artist in self.artists:
                self.artist_picked = artist
                self.pic_path = Path(self.config.pics_path) / artist
                self.pic_path = Path(self.config.vids_path) / artist
                break

            print("Not a valid option! Please try again.")

    def _select_random_video(self, viddir, min_duration=4):
        videos = [
            f
            for f in os.listdir(viddir)
            if not f.startswith(".") and f.endswith(".mp4")
        ]

        if not videos:
            print(f"No videos found in {viddir}")
            return None

        while videos:
            video = random.choice(videos)
            video_path = os.path.join(viddir, video)
            duration = FFcomms.get_duration(video_path)

            if duration >= min_duration:
                return video_path

            else:
                videos.remove(video)  # Remove the short video from the list

        print(
            f"No videos found with duration of at least {min_duration} seconds in {viddir}"
        )

        return None

    def check_picture_count(self, root_dir):
        pic_count = count_files(self.config.pics_path, os.path.isfile)
        folder_count = count_files(root_dir, os.path.isdir)

        if pic_count < folder_count:
            print(
                f"Not enough pictures in the specified folder! {folder_count - pic_count} pictures missing!"
            )
            sys.exit(1)

    def _check_duplicate_in_database(self, filename):
        return self.manager.beat_exists(filename)

    def _run(self, command):
        subprocess.run(
            command, check=True, stderr=subprocess.PIPE, universal_newlines=True
        )

    def _create_looping_video(self, input_path, output_path, audio_file, duration):
        ffmpeg_cmd = self.ffcomm.looping(input_path, output_path, audio_file, duration)
        self._run(ffmpeg_cmd)

    def create_thumbnail(self, picture_file, thumbnail_file):
        ffmpeg_cmd = self.ffcomm.thumbnail(picture_file, thumbnail_file)
        self._run(ffmpeg_cmd)

    def process_folder(self, folder_path, num, total):
        folder_path = Path(folder_path)

        # Remove current.wav files
        for file in folder_path.glob("*Current.wav"):
            file.unlink()

        # Find master file
        master_files = list(folder_path.glob("*Master.wav"))
        if not master_files:
            print(f"No master file found in {folder_path}")
            return
        master_file = master_files[0]

        # Check for duplicate
        if self._check_duplicate_in_database(master_file.stem):
            user_choice = input(
                f"Duplicate found for {master_file.stem}. Process anyway? (y/n): "
            ).lower()
            if user_choice != "y":
                print(f"Skipping folder {folder_path}")
                return

        # Zip stems
        print(f"Zipping file {num}/{total}")
        stems_folder = folder_path / "Stems"
        stems_folder.mkdir(exist_ok=True)
        for file in folder_path.iterdir():
            if "Master.wav" not in file.name and file.is_file():
                shutil.move(str(file), str(stems_folder))

        subprocess.run(
            [
                "7z",
                "a",
                "-tzip",
                "-r",
                "stems.zip",
                "Stems/",
                "-x!*.DS_Store",
                "-x!__MACOSX*",
            ],
            cwd=str(folder_path),
            stdout=subprocess.DEVNULL,
        )

        shutil.rmtree(stems_folder)
        zip_name = master_file.stem.replace("_Master", "_Stems") + ".zip"
        (folder_path / "stems.zip").rename(folder_path / zip_name)
        print("Zipping done!")

        # Create export folder for this beat
        export_folder = (
            Path(self.config.export_dir) / str(self.artist_picked) / master_file.stem
        )
        export_folder.mkdir(parents=True, exist_ok=True)

        # Render video
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                # Select and copy random picture to the folder_path
                pictures = [
                    f for f in os.listdir(self.pic_path) if not f.startswith(".")
                ]
                if not pictures:
                    print(f"No pictures found in {self.pic_path}")
                    return
                picture = random.choice(pictures)
                picture_path = os.path.join(self.pic_path, picture)
                dest_picture_path = folder_path / picture
                shutil.copy2(picture_path, dest_picture_path)

                # Select random video with minimum duration
                video_path = self._select_random_video(self.vid_path)

                if not video_path:
                    print(f"Failed to find a suitable video. Skipping this folder.")
                    return

                print(f"Rendering video {num}/{total} (Attempt {attempt + 1})")

                export_name = export_folder / f"{master_file.stem}.mp4"
                duration = FFcomms.get_duration(master_file)
                self._create_looping_video(
                    video_path,
                    str(export_name),
                    str(master_file),
                    duration,
                )
                print("Video rendering done!")

                # Create thumbnail
                thumbnail_path = export_folder / f"{master_file.stem}_thumbnail.jpg"
                thumb_cmd = self.ffcomm.thumbnail(
                    str(dest_picture_path), str(thumbnail_path)
                )
                self._run(thumb_cmd)
                print("Thumbnail created!")

                # Move picture to archive
                archive_dir = (
                    Path(self.pic_path).parent / "archive" / str(self.artist_picked)
                )
                archive_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(picture_path, archive_dir / picture)

                break  # If we get here, the video was rendered successfully

            except subprocess.CalledProcessError as e:
                print(f"Error during attempt {attempt + 1}: {str(e)}")
                if attempt == max_attempts - 1:
                    print(
                        f"Failed to render video after {max_attempts} attempts. Skipping this folder."
                    )
                    return

                else:
                    print("Retrying with a different video and picture...")

        # Render MP3
        print(f"Rendering MP3 {num}/{total}")
        mp3_name = os.path.join(
            self.config.mp3_dir, f"{master_file.stem} ({self.artist_picked}).mp3"
        )

        ffmpeg_cmd = self.ffcomm.mp3(master_file, mp3_name)
        self._run(ffmpeg_cmd)
        print("MP3 rendering done!")

        # Write filename to global filename list
        self.beatlist.append(master_file.stem)

    def data_write(self):
        self.manager.add_beats_from_filenames(self.beatlist)
        self.manager.close()  # TODO: check this, when it has to be closed. It might be wrong here


if __name__ == "__main__":
    processor = Process()
    processor.get_valid_artist()

    rootdir = UserPath()
    rootdir.read_while()

    processor.check_picture_count(rootdir.path)

    total_folders = sum(1 for _ in listdir_nohidden(rootdir.path))
    for num, folder in enumerate(listdir_nohidden(rootdir.path), 1):
        processor.process_folder(
            os.path.join(rootdir.path, folder),
            num,
            total_folders,
        )

    processor.data_write()
