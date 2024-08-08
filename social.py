import os
import subprocess
import re
import random
from pathlib import Path
import sys
import shlex

from beat_management import BeatManager, Beat

def process_video(video_path, beat_info, resource_folder, export_folder):
    # Extract necessary information from beat_info
    beat_name = beat_info[1]
    bpm = beat_info[4]
    
    # Calculate timing
    beat_time = float((1 / (int(bpm) / 60)) * 96)
    intro_delay = float((1 / (int(bpm) / 60)) * 16)
    
    # Get silence end time
    silence_end = get_silence_end(video_path)
    
    # Process each picture
    for picture_path in get_resource_files(resource_folder):
        output_path = export_folder / f"{beat_name}_{Path(picture_path).stem}.mp4"
        if create_video(video_path, picture_path, output_path, silence_end, intro_delay, beat_time):
            print(f"Successfully created: {output_path}")
        else:
            print(f"Failed to create: {output_path}")
    
    # Remove original video file
    try:
        os.remove(video_path)
        print(f"Removed original video: {video_path}")
    except OSError as e:
        print(f"Error removing original video: {e}")

def get_silence_end(video_path):
    try:
        ffmpeg_temp = f'ffmpeg -i "{video_path}" -ab 320k "social_temp.mp3"'
        subprocess.run(ffmpeg_temp, shell=True, check=True)
        
        ffmpeg_command = ["ffmpeg", "-i", "social_temp.mp3", "-af", "silencedetect=n=-50dB:d=1", "-f", "null", "-"]
        process = subprocess.Popen(ffmpeg_command, stderr=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)
        stdout_output, stderr_output = process.communicate()
        
        os.remove("social_temp.mp3")
        
        pattern = r'silence_end:\s*(\d+\.\d+)'
        match = re.search(pattern, stderr_output)
        return float(match.group(1)) if match else 0
    except subprocess.CalledProcessError as e:
        print(f"Error in get_silence_end: {e}")
        return 0
    except OSError as e:
        print(f"OS error in get_silence_end: {e}")
        return 0

def get_resource_files(resource_folder):
    return [f for f in resource_folder.iterdir() if f.is_file() and not f.name.startswith('.')]

def create_video(video_path, picture_path, output_path, silence_end, intro_delay, beat_time):
    try:
        temp_output = f"{output_path}_temp.mp4"
        filter_complex = (
            "[0:v]scale=-1:1440,perspective=0:0:W+250:-250:0:H:W+250:H+250,colorlevels=rimin=0.058:gimin=0.058:bimin=0.058:rimax=0.9:gimax=0.9:bimax=0.9,colorbalance=rs=0.1:gs=0.1:bs=0.1:rm=0.1:gm=0.1:bm=0.1:rh=0.1:gh=0.1:bh=0.1[v];"
            "[1:v][v]overlay=-325:480,hue=h={0}"
        ).format(random.randint(-360, 360))
        
        ffmpeg_command = [
            "ffmpeg",
            "-ss", f"{silence_end + intro_delay - 0.1}",
            "-to", f"{beat_time + silence_end}",
            "-i", str(video_path),
            "-i", str(picture_path),
            "-filter_complex", filter_complex,
            "-c:v", "libx264",
            "-crf", "17",
            "-b:a", "320k",
            "-preset", "slow",
            temp_output
        ]
        
        print("Executing FFmpeg command:")
        print(" ".join(shlex.quote(str(arg)) for arg in ffmpeg_command))
        
        subprocess.run(ffmpeg_command, check=True)
        
        ffmpeg_fin_command = [
            "ffmpeg",
            "-ss", "0.1",
            "-i", temp_output,
            "-c", "copy",
            output_path
        ]
        
        subprocess.run(ffmpeg_fin_command, check=True)
        
        os.remove(temp_output)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error in create_video: {e}")
        print(f"FFmpeg command output: {e.output}")
        return False
    except OSError as e:
        print(f"OS error in create_video: {e}")
        return False

def main():
    rootdir = input('Input the root directory path: ').strip("'\"")
    video_folder = Path(f'{rootdir}/videos')
    resource_folder = Path(f'{rootdir}/resources')
    export_folder = Path(f'{rootdir}/export')

    if not video_folder.exists() or not resource_folder.exists():
        print('Video folder or Resource folder does not exist!')
        sys.exit()

    # Create export folder if it doesn't exist
    export_folder.mkdir(exist_ok=True)

    beat_manager = BeatManager()

    for folder in video_folder.iterdir():
        if folder.is_dir():
            video_file = next((f for f in folder.iterdir() if f.suffix == '.mov'), None)
            if video_file:
                beat_info = beat_manager.search_beats(folder.name)
                if beat_info:
                    process_video(video_file, beat_info[0], resource_folder, export_folder)
                    beat_manager.update_social_media_video_flag(beat_info[0][0])
                    print(f"Updated social media flag for: {folder.name}")
                else:
                    print(f"No beat information found for {folder.name}")
            else:
                print(f"No .mov file found in {folder}")

    beat_manager.close()

if __name__ == "__main__":
    main()