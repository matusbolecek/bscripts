import os
import json
import pandas as pd
from typing import Dict, List
from dropbox_integration import process_files_with_dropbox

from beatstars_config import Publisher

def load_config(script_dir: str, config_file: str = f"{Publisher.resources_path}/publisher.json") -> Dict:
    config_path = os.path.join(script_dir, config_file)
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {config_path} not found.")
        print(f"Current working directory: {os.getcwd()}")
        print(f"Script directory: {script_dir}")
        return {}
    except json.JSONDecodeError:
        print(f"Error: {config_path} is not a valid JSON file.")
        return {}

def generate_youtube_data(config: Dict, beatname: str, download_link: str) -> Dict:
    yt_title = f"{config.get('YT_title', '')} \"{beatname}\""
    return {
        "Text": f"{config.get('YT_desc', '')}\n{yt_title}",
        "Year": None,
        "Month (1 to 12)": None,
        "Date": None,
        "Hour (From 0 to 23)": None,
        "Minutes": None,
        "Queue Schedule": "QLAST",
        "Post Type": "SHORTS",
        "Video Title": yt_title,
        "Video URL": download_link,
        "Thumbnail URL": None,
        "Subtitles URL": None,
        "Subtitles Language": None,
        "Subtitles Auto-Sync": None,
        "Privacy Status": "PUBLIC",
        "Category": "10",
        "Playlist": None,
        "Tags": config.get("YT_tags", ""),
        "License": "YOUTUBE",
        "Embeddable": "Yes",
        "Notify Subscribers": "No",
        "Made For Kids": "No"
    }

def generate_instagram_data(config: Dict, download_link: str) -> Dict:
    return {
        "Text": f"{config.get('IG_Text', '')}\n{config.get('IG_Comment', '')}",
        "Link": None,
        "Year": None,
        "Month (1 to 12)": None,
        "Date": None,
        "Hour (From 0 to 23)": None,
        "Minutes": None,
        "Queue Schedule": "QLAST",
        "Video Title": None,
        "Post Type": "REEL",
        "Image URL": None,
        "Alt Texts": None,
        "Video URL": download_link,
        "No. of Repetitions (From 1-10 OR 'FOREVER')": None,
        "Time Gap between Repetitions (Hours: From 1-24 OR 'WEEKLY' OR 'MONTHLY' OR 'YEARLY')": None,
        "Google Business Profile Type": None,
        "Google Business Profile URL": None,
        "Pinterest Title": None,
        "Pinterest Link": None,
        "Instagram First Comment": None,
        "Facebook First Comment": None,
        "LinkedIn First Comment": None,
        "TikTok First Comment": None,
        "Document URL": None,
        "Document Title": None
    }

def generate_tiktok_data(config: Dict, download_link: str) -> Dict:
    return {
        "Text": config.get("TT_Text", ""),
        "Link": None,
        "Year": None,
        "Month (1 to 12)": None,
        "Date": None,
        "Hour (From 0 to 23)": None,
        "Minutes": None,
        "Queue Schedule": "QLAST",
        "Video Title": None,
        "Post Type": "VIDEO",
        "Image URL": None,
        "Alt Texts": None,
        "Video URL": download_link,
        "No. of Repetitions (From 1-10 OR 'FOREVER')": None,
        "Time Gap between Repetitions (Hours: From 1-24 OR 'WEEKLY' OR 'MONTHLY' OR 'YEARLY')": None,
        "Google Business Profile Type": None,
        "Google Business Profile URL": None,
        "Pinterest Title": None,
        "Pinterest Link": None,
        "Instagram First Comment": None,
        "Facebook First Comment": None,
        "LinkedIn First Comment": None,
        "TikTok First Comment": None,
        "Document URL": None,
        "Document Title": None
    }

def save_to_csv(data: List[Dict], platform: str, export_folder: str, script_dir: str):
    if not data:
        print(f"No data to save for {platform}")
        return

    template_path = os.path.join(script_dir, f'{Publisher.resources_path}/Bulk_Uploader_Template.csv')
    if platform == 'youtube':
        template_path = os.path.join(script_dir, f'{Publisher.resources_path}/Bulk_Uploader_YouTube_Template.csv')

    try:
        template_df = pd.read_csv(template_path)
    except FileNotFoundError:
        print(f"Error: {template_path} not found.")
        return

    user_df = pd.DataFrame(data, columns=template_df.columns)
    
    # Create export folder if it doesn't exist
    export_folder_path = os.path.join(script_dir, export_folder)
    os.makedirs(export_folder_path, exist_ok=True)
    
    output_filename = os.path.join(export_folder_path, f'{platform}_output.csv')
    user_df.to_csv(output_filename, index=False)
    print(f"Data saved to {output_filename}")

def process_files(folder_path: str, export_folder: str, script_dir: str):
    config = load_config(script_dir)
    if not config:
        return

    youtube_data = []
    instagram_data = []
    tiktok_data = []

    folder_path = folder_path.strip("'\"")

    if not os.path.exists(folder_path):
        print(f"Error: The folder '{folder_path}' does not exist.")
        return

    try:
        dropbox_folder_name = "VideoUploads"  # You can change this name as needed
        file_generator = process_files_with_dropbox(folder_path, dropbox_folder_name)
        
        if file_generator is None:
            print("Error: Failed to initialize Dropbox upload process.")
            return

        for filename, download_link in file_generator:
            if download_link is None:
                print(f"Warning: Failed to upload {filename}. Skipping this file.")
                continue

            beatname, platform = filename.rsplit('.', 1)[0].rsplit('_', 1)
            
            if platform.lower() == 'yt':
                youtube_data.append(generate_youtube_data(config, beatname, download_link))
            elif platform.lower() == 'ig':
                instagram_data.append(generate_instagram_data(config, download_link))
            elif platform.lower() == 'tt':
                tiktok_data.append(generate_tiktok_data(config, download_link))
            else:
                print(f"Warning: Unknown platform '{platform}' for file {filename}. Skipping this file.")

    except Exception as e:
        print(f"Error processing files in '{folder_path}': {str(e)}")
        return

    if youtube_data:
        save_to_csv(youtube_data, 'youtube', export_folder, script_dir)
    if instagram_data:
        save_to_csv(instagram_data, 'instagram', export_folder, script_dir)
    if tiktok_data:
        save_to_csv(tiktok_data, 'tiktok', export_folder, script_dir)

    print("File processing complete.")

def get_valid_folder_path() -> str:
    while True:
        folder_path = input("Enter the folder path containing the video files: ").strip("'\"")
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            return folder_path
        else:
            print(f"Error: The folder '{folder_path}' does not exist or is not a directory. Please try again.")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    folder_path = get_valid_folder_path()
    export_folder = f"{folder_path}/export"
    process_files(folder_path, export_folder, script_dir)