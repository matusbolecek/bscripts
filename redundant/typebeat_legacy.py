import subprocess
import shlex
from pathlib import Path
import os

from beatstars_config import Typebeat, beatstars_folder
from typebeat import get_valid_artist

def get_user_input():
    video = input('Video filename: ')
    audio = input('Audio filename: ')
    return video, audio

def safe_path(path):
    # Convert to string if it's a Path object
    if isinstance(path, Path):
        path = str(path)
    # Remove any backslashes that might be escaping spaces or special characters
    path = path.replace('\\', '')
    # Use Path to handle the path and resolve it
    resolved_path = Path(path).expanduser().resolve()
    return shlex.quote(str(resolved_path))

def validate_file_path(file_path):
    # Remove any backslashes that might be escaping spaces or special characters
    if isinstance(file_path, str):
        file_path = file_path.replace('\\', '')
    path = Path(file_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return str(path)

def generate_export_paths(audio, artist):
    audio_stem = Path(audio).stem
    video_export = safe_path(Path(Typebeat.export_directory) / f"{audio_stem}.mp4")
    audio_export = safe_path(Path(Typebeat.mp3_directory) / f"{audio_stem} ({artist}).mp3")
    return video_export, audio_export

def create_ffmpeg_command(video, audio, video_export):
    watermark = safe_path(Typebeat.watermark)
    video = safe_path(video)
    audio = safe_path(audio)
    return (
        f'ffmpeg -threads 0 -framerate 24 -loop 1 -i {video} '
        f'-i {watermark} -i {audio} '
        '-filter_complex "[0:v]scale=-2:1080:flags=lanczos,'
        'pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black[base]; '
        '[1:v]scale=1920:-1:flags=lanczos[overlay]; '
        '[base][overlay]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2" '
        f'-c:a aac -c:v h264_videotoolbox -shortest {video_export}'
    )

def create_audio_command(audio, audio_export):
    return f'ffmpeg -i {safe_path(audio)} {audio_export}'

def run_command(command):
    result = subprocess.run(command, shell=True, executable="/bin/bash", capture_output=True, text=True)
    if result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, command, output=result.stdout, stderr=result.stderr)

def main():
    try:
        artist, _ = get_valid_artist()
        video, audio = get_user_input()
        
        video = validate_file_path(video)
        audio = validate_file_path(audio)
        video_export, audio_export = generate_export_paths(audio, artist)

        video_command = create_ffmpeg_command(video, audio, video_export)
        audio_command = create_audio_command(audio, audio_export)

        print(f"Executing video command: {video_command}")
        run_command(video_command)
        
        print(f"Executing audio command: {audio_command}")
        run_command(audio_command)

    except FileNotFoundError as e:
        print(f"Error: {e}")
        print(f"Current working directory: {os.getcwd()}")
        print(f"Directory contents: {os.listdir()}")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while running the command:")
        print(f"Command: {e.cmd}")
        print(f"Return code: {e.returncode}")
        print(f"Output: {e.output}")
        print(f"Error: {e.stderr}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()