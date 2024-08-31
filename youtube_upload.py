import os
import json
import pandas as pd
from typing import Dict, List, Tuple
import subprocess
import srt
from datetime import timedelta, datetime
import shutil

from dropbox_integration import process_files_with_dropbox
from beatstars_config import Publisher, Youtube, Management
from beat_management import BeatManager

def load_config(config_path: str) -> Dict:
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {config_path} not found.")
        return {}
    except json.JSONDecodeError:
        print(f"Error: {config_path} is not a valid JSON file.")
        return {}

def get_configs(channel_name: str) -> Tuple[Dict, Dict]:
    channel_config_path = os.path.join(Youtube.configs, f"{channel_name}.json")
    global_config_path = os.path.join(Youtube.configs, "global.json")
    
    channel_config = load_config(channel_config_path)
    global_config = load_config(global_config_path)
    
    if not channel_config:
        print(f"Error: Configuration for channel '{channel_name}' not found.")
    if not global_config:
        print("Error: Global configuration not found.")
    
    return channel_config, global_config

def get_video_duration(video_path: str) -> float:
    cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', video_path]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return float(result.stdout)

def generate_subtitles(video_path: str, beat_info: Dict, yt_title: str) -> str:
    duration = get_video_duration(video_path)
    subtitles = []
    
    for i in range(0, int(duration), 30):
        subtitles.extend([
            srt.Subtitle(index=i*3+1, start=timedelta(seconds=i), end=timedelta(seconds=i+10), content=yt_title),
            srt.Subtitle(index=i*3+2, start=timedelta(seconds=i+10), end=timedelta(seconds=i+20), content=f"{beat_info['key']} - {beat_info['tempo']} BPM"),
            srt.Subtitle(index=i*3+3, start=timedelta(seconds=i+20), end=timedelta(seconds=i+30), content="Purchase this beat at the link in the description (Buy 2 Get 1 Free!)")
        ])
    
    srt_content = srt.compose(subtitles)
    srt_path = video_path.rsplit('.', 1)[0] + '.srt'
    with open(srt_path, 'w') as f:
        f.write(srt_content)
    return srt_path

def generate_description(beat_info: Dict, channel_config: Dict, global_config: Dict, yt_title: str) -> str:
    description = f"""💰 Purchase This Beat (Untagged) | {beat_info.get('download_link', '')}

{global_config.get('Pack', '')}

BPM: {beat_info.get('tempo', '')}
KEY: {beat_info.get('key', '')}

Instagram: https://www.instagram.com/matejcikbeats
Email: matejcikbeats@gmail.com
Beat Store: https://matejcikbeats.beatstars.com/

Prod. {beat_info.get('collaborators', '')}

This instrumental is free to use for non-profit use. If you have any questions, please contact me.
A license must be purchased to use for profit (Streaming Services, music videos, etc.)
Must Credit: (prod. matejcikbeats)

TAGS (IGNORE):
{yt_title}
{channel_config.get('Gpt', '')}

Some other ways I would describe this beat:
{', '.join(channel_config.get('Tags', []))}"""
    return description

def generate_youtube_data(channel_config: Dict, global_config: Dict, beat_info: Dict, download_link: str, subtitles_link: str, thumbnail_link: str) -> Dict:
    config = {**global_config, **channel_config}
    
    yt_title = f"{config.get('YT_title', '')} \"{beat_info['name']}\""
    description = generate_description(beat_info, channel_config, global_config, yt_title)
    
    return {
        "Text": description,
        "Year": None,
        "Month (1 to 12)": None,
        "Date": None,
        "Hour (From 0 to 23)": None,
        "Minutes": None,
        "Queue Schedule": "QLAST",
        "Post Type": "VIDEO",
        "Video Title": yt_title,
        "Video URL": download_link,
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
        "Made For Kids": "No"
    }

def save_to_csv(data: List[Dict], channel_name: str, script_dir: str):
    if not data:
        print("No data to save")
        return

    template_path = os.path.join(script_dir, f'{Publisher.resources_path}/Bulk_Uploader_YouTube_Template.csv')

    try:
        template_df = pd.read_csv(template_path)
    except FileNotFoundError:
        print(f"Error: {template_path} not found.")
        return

    user_df = pd.DataFrame(data, columns=template_df.columns)
    
    current_time = datetime.now()
    output_filename = f"{channel_name}_{current_time.strftime('%Y-%m-%d_%H-%M-%S')}.csv"
    output_path = os.path.join(script_dir, output_filename)
    user_df.to_csv(output_path, index=False)
    print(f"Data saved to {output_path}")

def process_files_with_dropbox(local_folder, dropbox_folder, dropbox_instance):
    print(f"Uploading files from {local_folder} to Dropbox folder {dropbox_folder}")
    for filename in os.listdir(local_folder):
        file_path = os.path.join(local_folder, filename)
        try:
            # Your existing upload code here
            # This is a placeholder. Replace with actual Dropbox upload logic
            print(f"Simulating upload of {filename} to Dropbox")
            download_link = f"https://www.dropbox.com/home/{dropbox_folder}/{filename}"
            print(f"Successfully uploaded file: {filename}")
            yield filename, download_link
        except Exception as e:
            print(f"Error uploading {filename} to Dropbox: {str(e)}")
            yield filename, None

def process_files(folder_path: str, channel_name: str, channel_config: Dict, global_config: Dict, beat_manager: BeatManager):
    youtube_data = []
    processed_files = []

    folder_path = folder_path.strip("'\"")

    if not os.path.exists(folder_path):
        print(f"Error: The folder '{folder_path}' does not exist.")
        return

    try:
        dropbox_folder_name = "VideoUploads"
        
        # Get list of video files
        video_files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.mp4', '.avi', '.mov', '.wmv'))]
        
        if not video_files:
            print(f"No video files found in {folder_path}")
            return

        all_uploads_successful = True

        for filename in video_files:
            print(f"Processing file: {filename}")
            file_path = os.path.join(folder_path, filename)
            
            try:
                # Simulate Dropbox upload (replace with actual upload logic)
                print(f"Simulating upload of {filename} to Dropbox")
                download_link = f"https://www.dropbox.com/home/{dropbox_folder_name}/{filename}"
                print(f"Successfully uploaded file: {filename}")
            except Exception as e:
                print(f"Error uploading {filename} to Dropbox: {str(e)}")
                all_uploads_successful = False
                continue

            beatname = filename.rsplit('.', 1)[0].rsplit('_', 1)[0]
            
            beat_results = beat_manager.search_beats(beatname, search_by='name')
            if not beat_results:
                print(f"Warning: Beat '{beatname}' not found in the database. Skipping this file.")
                all_uploads_successful = False
                continue

            beat = beat_results[0]
            if len(beat) < 5:  # Ensure we have all required beat information
                print(f"Warning: Incomplete beat information for '{beatname}'. Skipping this file.")
                all_uploads_successful = False
                continue

            beat_info = {
                'name': beat[1],
                'collaborators': beat[2],
                'key': beat[3],
                'tempo': beat[4],
            }

            filename_info = BeatManager.parse_filename(filename)
            
            if beat_info['key'] != filename_info.key or beat_info['tempo'] != filename_info.tempo:
                print(f"Warning: Mismatch in key or BPM for '{beatname}'. Database: {beat_info['key']}, {beat_info['tempo']} BPM. Filename: {filename_info.key}, {filename_info.tempo} BPM. Skipping this file.")
                all_uploads_successful = False
                continue

            yt_title = f"{channel_config.get('YT_title', '')} \"{beatname}\""
            srt_path = generate_subtitles(file_path, beat_info, yt_title)
            
            # Simulate SRT upload (replace with actual upload logic)
            print(f"Simulating upload of SRT file for {filename} to Dropbox")
            srt_link = f"https://www.dropbox.com/home/{dropbox_folder_name}/subtitles/{os.path.basename(srt_path)}"
            print(f"Successfully uploaded SRT file for: {filename}")

            thumbnail_filename = f"{beatname}_thumbnail.jpg"
            thumbnail_path = os.path.join(folder_path, thumbnail_filename)
            if os.path.exists(thumbnail_path):
                # Simulate thumbnail upload (replace with actual upload logic)
                print(f"Simulating upload of thumbnail for {filename} to Dropbox")
                thumbnail_link = f"https://www.dropbox.com/home/{dropbox_folder_name}/thumbnails/{thumbnail_filename}"
                print(f"Successfully uploaded thumbnail for: {filename}")
            else:
                print(f"Warning: Thumbnail for {beatname} not found. Using default thumbnail.")
                thumbnail_link = channel_config.get('default_thumbnail_url', None)
            
            beat_info['download_link'] = download_link
            
            youtube_data.append(generate_youtube_data(channel_config, global_config, beat_info, download_link, srt_link, thumbnail_link))
            processed_files.append(file_path)

        if all_uploads_successful:
            print("All files uploaded successfully. Deleting processed files.")
            for file_path in processed_files:
                try:
                    os.remove(file_path)
                    print(f"Deleted: {file_path}")
                except Exception as e:
                    print(f"Error deleting {file_path}: {str(e)}")
        else:
            print("Some uploads failed. No files will be deleted.")

    except Exception as e:
        print(f"Error processing files in '{folder_path}': {str(e)}")
        return

    if youtube_data:
        save_to_csv(youtube_data, channel_name, os.path.dirname(os.path.abspath(__file__)))

    print("File processing complete.")

def get_valid_folder_path() -> str:
    while True:
        folder_path = input("Enter the folder path containing the video files: ").strip("'\"")
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            return folder_path
        else:
            print(f"Error: The folder '{folder_path}' does not exist or is not a directory. Please try again.")

def main():
    channel_name = input("Enter the YouTube channel name: ")
    channel_config, global_config = get_configs(channel_name)
    if not channel_config or not global_config:
        return

    folder_path = get_valid_folder_path()
    
    beat_manager = BeatManager(Management.database_path_beats)
    process_files(folder_path, channel_name, channel_config, global_config, beat_manager)
    beat_manager.close()

if __name__ == "__main__":
    main()