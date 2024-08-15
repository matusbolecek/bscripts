import os
import re
import subprocess
import time
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler

from beat_management import BeatManager, Beat
from beatstars_config import Beatpack, Management
from beatstars import bpm_convert

# Set up logging
log_file = 'log_folder/loop_kit_error.log'
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
handler = RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=5)
handler.setLevel(logging.ERROR)
logger = logging.getLogger('')
logger.addHandler(handler)

def parse_loop_filename(filename: str) -> Beat:
    name_parts = filename.rsplit('.', 1)[0].split()
    
    collaborators = "@matejcikbeats"
    if 'x' in name_parts:
        x_index = name_parts.index('x')
        collaborators_parts = name_parts[x_index-1:]
        collaborators = ', '.join([part.strip('@') for part in collaborators_parts if part != 'x'])
        name_parts = name_parts[:x_index-1]
    elif name_parts[-1].startswith('@'):
        collaborators = name_parts[-1]
        name_parts = name_parts[:-1]
    
    tempo = int(name_parts[-2])
    key = name_parts[-1]
    name = ' '.join(name_parts[:-2])
    
    return Beat(name=name, collaborators=collaborators, key=key, tempo=tempo)

def process_loops(full_folder, video_folder, output_folder, pack_name):
    beat_manager = BeatManager(Management.database_path_loops)
    
    resources_folder = os.path.join(output_folder, 'Resources')
    os.makedirs(resources_folder, exist_ok=True)
    
    youtube_loops = []
    all_loops = []
    
    logging.info(f"Files in full folder: {os.listdir(full_folder)}")
    logging.info(f"Files in video folder: {os.listdir(video_folder)}")
    
    for filename in sorted(os.listdir(full_folder)):
        if filename.endswith('.wav') or filename.endswith('.mp3'):
            loop = parse_loop_filename(filename)
            loop.pack = pack_name
            
            existing_loops = beat_manager.search_beats(loop.name, search_by='name')
            
            if existing_loops:
                logging.debug(f"search_beats returned: {existing_loops[0]}")
                loop_id, *_, existing_pack = existing_loops[0]
                if existing_pack and existing_pack != 'None':
                    logging.info(f"Loop '{loop.name}' is already in pack '{existing_pack}'. Skipping...")
                    continue
                
                beat_manager.update_pack(loop_id, pack_name)
                logging.info(f"Updated pack for existing loop: {loop.name}")
            else:
                beat_manager.add_beat(loop)
                logging.info(f"Added new loop to database: {loop.name}")
            
            all_loops.append(loop)
            
            video_filename, order_number = find_matching_file(filename, video_folder)
            if video_filename:
                youtube_loops.append((int(order_number), loop))
                output_filename = f"{order_number}_{loop.name}.wav"
                output_path = os.path.join(resources_folder, output_filename)
                temp_time = bpm_convert(loop.tempo, 8)
                ffmpeg_command = f'ffmpeg -to {temp_time} -i "{os.path.join(video_folder, video_filename)}" -af "silenceremove=start_periods=1:start_duration=0:start_threshold=-50dB" -ab 320k "{output_path}"'
                try:
                    subprocess.run(ffmpeg_command, shell=True, executable="/bin/bash", check=True, capture_output=True, text=True)
                    logging.info(f"Generated short version for video: {output_filename}")
                except subprocess.CalledProcessError as e:
                    logging.error(f"Error generating short version for {loop.name}: {str(e)}")
                    logging.error(f"FFmpeg stderr: {e.stderr}")
            else:
                logging.warning(f"No matching file found in video folder for: {filename}")

    if not youtube_loops:
        logging.warning("No matching files were found in the video folder. SRT and timestamps will be empty.")
    else:
        # Sort youtube_loops based on the order number
        youtube_loops.sort(key=lambda x: x[0])
        # Extract just the loops from the sorted list
        sorted_youtube_loops = [loop for _, loop in youtube_loops]
        generate_srt_subtitles(sorted_youtube_loops, output_folder)
        generate_youtube_timestamps(sorted_youtube_loops, output_folder)
    
    beat_manager.close()

def find_matching_file(filename, folder):
    base_name = os.path.splitext(filename)[0].lower()
    base_parts = re.split(r'\s+', base_name)
    
    logging.debug(f"Searching for match for file: {filename}")
    logging.debug(f"Base parts: {base_parts}")
    
    for file in os.listdir(folder):
        file_lower = file.lower()
        match = re.match(r'^(\d+)\s+(.+)', file_lower)
        if match:
            order_number = match.group(1)
            file_parts = re.split(r'\s+', match.group(2))
            
            logging.debug(f"Checking file: {file}")
            logging.debug(f"File parts: {file_parts}")
            
            # Check if all parts of the base_name are in the file_parts
            if all(any(base_part in file_part for file_part in file_parts) for base_part in base_parts):
                logging.info(f"Match found: {file}")
                return file, order_number
    
    logging.debug("No match found")
    return None, None

def generate_srt_subtitles(loops, output_folder):
    srt_path = os.path.join(output_folder, 'subtitles.srt')
    
    with open(srt_path, 'w') as f:
        start_time = 0
        for i, loop in enumerate(loops, 1):
            end_time = start_time + bpm_convert(loop.tempo, 8)
            
            f.write(f"{i}\n")
            f.write(f"{format_time(start_time)} --> {format_time(end_time)}\n")
            f.write(f'"{loop.name}" - {loop.tempo} BPM {loop.key}\n')
            f.write(f'prod. by {loop.collaborators}\n\n')
            
            start_time = end_time
    
    logging.info(f"Generated SRT subtitles for YouTube video")

def generate_youtube_timestamps(loops, output_folder):
    timestamp_path = os.path.join(output_folder, 'youtube_timestamps.txt')
    
    with open(timestamp_path, 'w') as f:
        current_time = 0
        for loop in loops:
            f.write(f"{format_time(current_time, youtube=True)} - {loop.name} ({loop.key})\n")
            current_time += bpm_convert(loop.tempo, 8)
    
    logging.info(f"Generated YouTube timestamps")

def format_time(seconds, youtube=False):
    if youtube:
        return time.strftime('%M:%S', time.gmtime(seconds))
    return time.strftime('%H:%M:%S,000', time.gmtime(seconds))

if __name__ == "__main__":
    full_folder = input("Enter the path to the full loops folder: ").strip("'").strip('"')
    video_folder = input("Enter the path to the video loops folder: ").strip("'").strip('"')
    output_folder = input("Enter the path to the output folder: ").strip("'").strip('"')
    pack_name = input("Enter the name of the loop pack: ").strip()
    
    if not os.path.isdir(full_folder):
        logging.error(f"The full loops folder '{full_folder}' does not exist.")
    elif not os.path.isdir(video_folder):
        logging.error(f"The video loops folder '{video_folder}' does not exist.")
    elif not os.path.isdir(output_folder):
        logging.error(f"The output folder '{output_folder}' does not exist.")
    else:
        try:
            process_loops(full_folder, video_folder, output_folder, pack_name)
            logging.info("Loop processing completed successfully!")
        except Exception as e:
            logging.exception(f"An error occurred during processing: {str(e)}")