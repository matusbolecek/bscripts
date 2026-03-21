import fnmatch
from pathlib import Path
import sys
import os
import subprocess
import shutil
import random

from beatstars_config import Typebeat, beatstars_folder, Management
from beatstars import listdir_nohidden
from beat_management import BeatManager


def get_valid_artist():
    artists = ["nardo", "future", "southside", "rob49"]
    while True:
        artist = input(f"Choose an artist ({' / '.join(artists)}): ")
        if artist in artists:
            return (
                artist,
                f"{Typebeat.pictures}/{artist}",
                f"{Typebeat.videos}/{artist}",
            )
        print("Not a valid option! Please try again.")


def get_video_duration(video_path):
    ffprobe_cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    try:
        duration = float(subprocess.check_output(ffprobe_cmd).decode("utf-8").strip())
        return duration
    except subprocess.CalledProcessError:
        return 0  # Return 0 if there's an error getting the duration


def select_random_video(viddir, min_duration=4):
    videos = [
        f for f in os.listdir(viddir) if not f.startswith(".") and f.endswith(".mp4")
    ]
    if not videos:
        print(f"No videos found in {viddir}")
        return None

    while videos:
        video = random.choice(videos)
        video_path = os.path.join(viddir, video)
        duration = get_video_duration(video_path)

        if duration >= min_duration:
            return video_path
        else:
            videos.remove(video)  # Remove the short video from the list

    print(
        f"No videos found with duration of at least {min_duration} seconds in {viddir}"
    )
    return None


def count_files(directory, condition):
    return sum(
        1
        for path in listdir_nohidden(directory)
        if condition(os.path.join(directory, path))
    )


def check_picture_count(pic_dir, root_dir):
    pic_count = count_files(pic_dir, os.path.isfile)
    folder_count = count_files(root_dir, os.path.isdir)
    if pic_count < folder_count:
        print(
            f"Not enough pictures in the specified folder! {folder_count - pic_count} pictures missing!"
        )
        sys.exit(1)


def check_duplicate_in_database(filename):
    manager = BeatManager(Management.database_path_beats)
    is_duplicate = manager.beat_exists(filename)
    manager.close()
    return is_duplicate


def create_looping_video(
    input_video, output_video, audio_file, watermark_black, duration
):
    ffmpeg_cmd = [
        "ffmpeg",
        "-stream_loop",
        "-1",  # Loop the input video
        "-i",
        input_video,
        "-i",
        audio_file,
        "-i",
        watermark_black,
        "-filter_complex",
        "[0:v]trim=start_frame=1,scale=-2:1080:flags=lanczos,setsar=1[v]; \
         [v][0:v]concat=n=2:v=1[looped]; \
         [looped]scale=-2:1080:flags=lanczos,setsar=1[scaled_video]; \
         [2:v][scaled_video]overlay=(W-w)/2:(H-h)/2:format=auto,format=yuv420p[final]",
        "-map",
        "[final]",
        "-map",
        "1:a",
        "-shortest",
        "-c:v",
        "h264_videotoolbox",
        "-c:a",
        "aac",
        "-t",
        str(duration),
        output_video,
    ]
    subprocess.run(
        ffmpeg_cmd, check=True, stderr=subprocess.PIPE, universal_newlines=True
    )


def create_thumbnail(picture_file, watermark_black, thumbnail_file):
    ffmpeg_cmd = [
        "ffmpeg",
        "-i",
        watermark_black,
        "-i",
        picture_file,
        "-filter_complex",
        "[1:v]scale=-2:1080:flags=lanczos[pic];[0:v][pic]overlay=(W-w)/2:(H-h)/2",
        "-frames:v",
        "1",
        thumbnail_file,
    ]
    subprocess.run(
        ffmpeg_cmd, check=True, stderr=subprocess.PIPE, universal_newlines=True
    )


def process_folder(folder_path, picdir, viddir, artist, num, total, beatlist):
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
    if check_duplicate_in_database(master_file.stem):
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
    export_folder = Path(Typebeat.export_directory) / artist / master_file.stem
    export_folder.mkdir(parents=True, exist_ok=True)

    # Render video
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            # Select and copy random picture to the folder_path
            pictures = [f for f in os.listdir(picdir) if not f.startswith(".")]
            if not pictures:
                print(f"No pictures found in {picdir}")
                return
            picture = random.choice(pictures)
            picture_path = os.path.join(picdir, picture)
            dest_picture_path = folder_path / picture
            shutil.copy2(picture_path, dest_picture_path)

            # Select random video with minimum duration
            video_path = select_random_video(viddir)
            if not video_path:
                print(f"Failed to find a suitable video. Skipping this folder.")
                return

            print(f"Rendering video {num}/{total} (Attempt {attempt + 1})")
            export_name = export_folder / f"{master_file.stem}.mp4"

            # Get audio duration
            ffprobe_cmd = [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(master_file),
            ]
            duration = float(
                subprocess.check_output(ffprobe_cmd).decode("utf-8").strip()
            )

            create_looping_video(
                video_path,
                str(export_name),
                str(master_file),
                str(Typebeat.watermark_black),
                duration,
            )
            print("Video rendering done!")

            # Create thumbnail
            thumbnail_path = export_folder / f"{master_file.stem}_thumbnail.jpg"
            create_thumbnail(
                str(dest_picture_path),
                str(Typebeat.watermark_black),
                str(thumbnail_path),
            )
            print("Thumbnail created!")

            # Move picture to archive
            archive_dir = Path(picdir).parent / "archive" / artist
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
        Typebeat.mp3_directory, f"{master_file.stem} ({artist}).mp3"
    )
    subprocess.run(
        ["ffmpeg", "-i", str(master_file), "-ab", "320k", mp3_name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )
    print("MP3 rendering done!")

    # Write filename to global filename list
    beatlist.append(master_file.stem)


def data_write(beatlist):
    manager = BeatManager(Management.database_path_beats)
    manager.add_beats_from_filenames(beatlist)
    manager.close()


if __name__ == "__main__":
    artist, picdir, viddir = get_valid_artist()
    beat_names = []

    rootdir = input("Input the root directory path: ")
    rootdir = rootdir.strip("'\"")  # Remove any surrounding quotes
    rootdir = rootdir.replace("\\ ", " ")  # Replace escaped spaces with actual spaces
    rootdir = os.path.expanduser(rootdir)  # Expand user directory if present (e.g., ~)
    rootdir = os.path.abspath(rootdir)  # Convert to absolute path

    if not os.path.exists(rootdir):
        print(f"The directory '{rootdir}' does not exist.")
        sys.exit(1)

    check_picture_count(picdir, rootdir)

    total_folders = sum(1 for _ in listdir_nohidden(rootdir))
    for num, folder in enumerate(listdir_nohidden(rootdir), 1):
        process_folder(
            os.path.join(rootdir, folder),
            picdir,
            viddir,
            artist,
            num,
            total_folders,
            beat_names,
        )

    data_write(beat_names)

