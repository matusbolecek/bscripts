import os
import re
import subprocess
import time
from pathlib import Path

from beat_management import BeatManager, Beat
from beatstars_config import Beatpack, Management
from beatstars import bpm_convert

def parse_loop_filename(filename: str) -> Beat:
    # Remove file extension
    name_parts = filename.rsplit('.', 1)[0].split()
    
    # Extract collaborators
    collaborators = "@matejcikbeats"
    if 'x' in name_parts:
        x_index = name_parts.index('x')
        collaborators_parts = name_parts[x_index-1:]
        collaborators = ', '.join([part.strip('@') for part in collaborators_parts if part != 'x'])
        name_parts = name_parts[:x_index-1]
    elif name_parts[-1].startswith('@'):
        collaborators = name_parts[-1]
        name_parts = name_parts[:-1]
    
    # Extract tempo and key
    tempo = int(name_parts[-2])
    key = name_parts[-1]
    
    # Extract name
    name = ' '.join(name_parts[:-2])
    
    return Beat(name=name, collaborators=collaborators, key=key, tempo=tempo)

def process_loops(full_folder, video_folder, output_folder, pack_name):
    beat_manager = BeatManager(Management.database_path_loops)
    
    # Create Resources folder if it doesn't exist
    resources_folder = os.path.join(output_folder, 'Resources')
    os.makedirs(resources_folder, exist_ok=True)
    
    # Process full folder
    for filename in os.listdir(full_folder):
        if filename.endswith('.wav') or filename.endswith('.mp3'):
            loop = parse_loop_filename(filename)
            loop.pack = pack_name
            
            # Search for existing loop in database
            existing_loops = beat_manager.search_beats(loop.name, search_by='name')
            
            if existing_loops:
                # Update pack for existing loop
                loop_id = existing_loops[0][0]  # Assuming the ID is the first element
                beat_manager.update_pack(loop_id, pack_name)
                print(f"Updated pack for existing loop: {loop.name}")
            else:
                # Add new loop to database
                beat_manager.add_beat(loop)
                print(f"Added new loop to database: {loop.name}")
            
            # Generate short version for video
            if filename in os.listdir(video_folder):
                output_path = os.path.join(resources_folder, f"{loop.name}.wav")
                temp_time = bpm_convert(loop.tempo, 8)
                ffmpeg_command = f'ffmpeg -to {temp_time} -i "{os.path.join(full_folder, filename)}" -af "silenceremove=start_periods=1:start_duration=0:start_threshold=-50dB" -ab 320k "{output_path}"'
                try:
                    subprocess.run(ffmpeg_command, shell=True, executable="/bin/bash", check=True)
                    print(f"Generated short version for video: {loop.name}")
                except subprocess.CalledProcessError as e:
                    print(f"Error generating short version for {loop.name}: {str(e)}")

    # Generate SRT subtitles
    generate_srt_subtitles(beat_manager, output_folder, pack_name)

    beat_manager.close()

def generate_srt_subtitles(beat_manager, output_folder, pack_name):
    all_loops = beat_manager.search_beats(pack_name, search_by='pack')
    srt_path = os.path.join(output_folder, 'subtitles.srt')
    
    with open(srt_path, 'w') as f:
        start_time = 0
        for i, loop in enumerate(all_loops, 1):
            end_time = start_time + bpm_convert(loop[4], 8)  # Assuming tempo is at index 4
            
            f.write(f"{i}\n")
            f.write(f"{format_time(start_time)} --> {format_time(end_time)}\n")
            f.write(f'"{loop[1]}" - {loop[3]} {loop[4]}BPM\n\n')  # Assuming name is at index 1, key at 3, and tempo at 4
            
            start_time = end_time
    
    print(f"Generated SRT subtitles for {pack_name}")

def format_time(seconds):
    return time.strftime('%H:%M:%S,000', time.gmtime(seconds))

if __name__ == "__main__":
    full_folder = input("Enter the path to the full loops folder: ").strip("'").strip('"')
    video_folder = input("Enter the path to the video loops folder: ").strip("'").strip('"')
    output_folder = input("Enter the path to the output folder: ").strip("'").strip('"')
    pack_name = input("Enter the name of the loop pack: ").strip()
    
    # Validate directory existence
    if not os.path.isdir(full_folder):
        print(f"Error: The full loops folder '{full_folder}' does not exist.")
    elif not os.path.isdir(video_folder):
        print(f"Error: The video loops folder '{video_folder}' does not exist.")
    elif not os.path.isdir(output_folder):
        print(f"Error: The output folder '{output_folder}' does not exist.")
    else:
        try:
            process_loops(full_folder, video_folder, output_folder, pack_name)
            print("Loop processing completed successfully!")
        except Exception as e:
            print(f"An error occurred during processing: {str(e)}")