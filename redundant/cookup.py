import json
import os
import random
import subprocess
import sys
from pathlib import Path
from typing import List, Dict
import fnmatch
import shutil

from beatstars_config import Cookup, beatstars_folder, Management
from video_picker import generator
from beatstars import listdir_nohidden, bpm_convert, dircheck, silence_read
from beat_management import BeatManager

def write_json(path: str) -> None:
    # Write a default JSON file with video properties
    props = {
        "video_bpm": " ",
        "cookup_start": " ",
        "cookup_end": " ",
        "loop_text": " ",
        "intro_length_bars": "12",
        "preview_length_bars": "24"
    }
    with open(f'{path}/props.json', 'w') as f:
        json.dump(props, f, indent=4)

def process_folder(folder_path: Path, rootdir: str) -> None:
    # Process a single folder containing video files and props.json
    file_list = []
    json_in_folder = False

    for file in folder_path.iterdir():
        if file.suffix in ('.mov', '.mp4'):
            file_list.append(file)
        elif file.name == 'props.json':
            json_in_folder = True

    if len(file_list) != 2 or not json_in_folder:
        print(f'Error in folder {folder_path.name}! Exactly 2 video files and props.json must be in every folder.')
        return

    with open(folder_path / "props.json", "r") as f:
        props = json.load(f)

    try:
        props["video_bpm"] = float(props["video_bpm"])
    except ValueError:
        print(f"Error: Invalid 'video_bpm' value in {folder_path.name}/props.json. Must be a valid number.")
        return

    final_directory = Path(rootdir) / 'export' / folder_path.name
    final_directory.mkdir(exist_ok=True)
    file_list.sort()

    process_intro(file_list, props, final_directory)
    process_main_video(file_list, props, final_directory)
    process_preview(file_list, props, final_directory)
    combine_videos(final_directory, rootdir, props)

def process_intro(file_list: List[Path], props: Dict, final_directory: Path) -> None:
    # Process the intro part of the video
    audio_start = silence_read(file_list[1])
    intro_end = audio_start + bpm_convert(props["video_bpm"], 4 + int(props["intro_length_bars"]))
    
    ffmpeg_command = f'''ffmpeg -i "{file_list[1]}" -ss {audio_start + bpm_convert(props["video_bpm"], 4)} -to {intro_end} -vn -acodec copy "{final_directory}/audio.aac"'''
    subprocess.run(ffmpeg_command, shell=True, executable="/bin/bash")

    tag_file = random.choice([f'{Cookup.cookup_materials}/tags/alttag_12bar.wav', f'{Cookup.cookup_materials}/tags/tag_12bar.wav']) if int(props["intro_length_bars"]) == 12 else f'{Cookup.cookup_materials}/tags/tag_xbar.wav'
    tag_command = f'''ffmpeg -i "{tag_file}" -filter:a "atempo={(18 / bpm_convert(props["video_bpm"], 12))}" "{final_directory}/tag.wav"'''
    subprocess.run(tag_command, shell=True, executable="/bin/bash")

    generator(f'{Cookup.cookup_alt_materials}/cut_clips/future', 1, final_directory, 8)
    
    intro_command = f'''ffmpeg -i "{final_directory}/1.mp4" -i "{Cookup.cookup_alt_materials}/overlay.mov" -i "{Cookup.cookup_materials}/intro.png" -i "{final_directory}/audio.aac" -i "{final_directory}/tag.wav" \
    -filter_complex "[0:v]boxblur=40,scale=2560x1440,setsar=1[bg]; \
    [0:v]scale=1440:1440:force_original_aspect_ratio=decrease[fg]; \
    [bg][fg]overlay=x=(W-w)/2:y=(H-h)/2[base]; \
    [base][1:v]blend=all_mode=softlight:all_opacity=0.3[softlight]; \
    [softlight][2:v]overlay=(W-w)/2:(H-h)/2[v]; \
    [3:a][4:a]amix=inputs=2:duration=longest:normalize=0[a]" \
    -map "[v]" -map "[a]" -c:v h264 -c:a aac -b:a 320k -to {bpm_convert(props["video_bpm"], 12)} "{final_directory}/first.mov"'''
    subprocess.run(intro_command, shell=True, executable="/bin/bash")

    for file in ['tag.wav', '1.mp4', 'audio.aac']:
        (final_directory / file).unlink()

def process_main_video(file_list: List[Path], props: Dict, final_directory: Path) -> None:
    # Process the main part of the video
    main_command = f'''ffmpeg -ss {props["cookup_start"]} -to {props["cookup_end"]} -i "{file_list[0]}" \
    -filter_complex "[0:v]fps=60,drawtext=fontfile='{Cookup.cookup_materials}/font.ttf': \
    text='{props["loop_text"]}': \
    x=(w-text_w)/2: \
    y=h-(text_h*2): \
    fontsize=64: \
    fontcolor=white: \
    alpha='if(lt(t,5),0,if(lt(t,6),(t-5)/1,if(lt(t,14),1,if(lt(t,15),(1-(t-14))/1,0))))'[v]" \
    -map "[v]" -map 0:a -c:v libx264 -preset fast -crf 18 -c:a aac -b:a 320k "{final_directory}/second.mov"'''
    
    subprocess.run(main_command, shell=True, executable="/bin/bash")

def process_preview(file_list: List[Path], props: Dict, final_directory: Path) -> None:
    # Process the preview part of the video
    lut_file = random.choice(list(Path(Cookup.lut_path).glob('*.cube')))
    audio_start = silence_read(file_list[1])
    preview_end = audio_start + bpm_convert(props["video_bpm"], int(props["preview_length_bars"]))

    preview_command = f'''ffmpeg -ss {audio_start} -to {preview_end} -i "{file_list[1]}" -i "{Cookup.cookup_materials}/outro.png" \
    -filter_complex "[0:v]fps=60,lut3d='{lut_file}'[video];[video][1:v]overlay=0:0" \
    -c:v libx264 -preset fast -crf 18 -c:a aac -b:a 320k "{final_directory}/third.mov"'''
    
    subprocess.run(preview_command, shell=True, executable="/bin/bash")

def save_preview(file_list: List[Path], final_directory: Path):
    final_directory = f'{Cookup.cookup_exports}/social/{final_directory.name}'
    dircheck(final_path)
    shutil.copyfile(file_list[1], final_directory)

def update_tutorial_made_flag(beat_name: str) -> None:
    # Update the tutorial_made flag in the database for the given beat name.
    beat_manager = BeatManager(Management.database_path_beats)
    all_beats = beat_manager.get_all_beats()
    
    for beat in all_beats:
        if beat[1].lower() == beat_name.lower():  # Compare beat names case-insensitively
            beat_manager.update_tutorial_flag(beat[0])  # Update the flag
            print(f"Updated tutorial_made flag for beat: {beat_name}")
            break
    else:
        print(f"Beat not found in database: {beat_name}")
    
    beat_manager.close()

def run_ffmpeg_and_update_db(command: str, beat_name: str) -> None:
    # Run the ffmpeg command and update the database only if successful.
    try:
        subprocess.run(command, shell=True, executable="/bin/bash", check=True)
        print("Video rendering completed successfully.")
        
        update_tutorial_made_flag(beat_name)
    except subprocess.CalledProcessError as e:
        print(f"Error occurred during video rendering: {e}")
        print("Database not updated due to rendering failure.")

def combine_videos(final_directory: Path, root_folder: Path, props: Dict) -> None:
    # Stretch the riser to match tempo of track
    tag_command = f'''ffmpeg -i "{Cookup.cookup_materials}/riser_16bar.wav" -filter:a "atempo={(24 / bpm_convert(props["video_bpm"], 16))}" "{final_directory}/riser_stretched.wav"'''
    subprocess.run(tag_command, shell=True, executable="/bin/bash")

    # Combine all processed video parts into a final video
    combine_command = f'''ffmpeg -i {final_directory}/first.mov -i {final_directory}/second.mov -i {final_directory}/third.mov -i "{final_directory}/riser_stretched.wav" \
    -filter_complex "[0:v][0:a][1:v][1:a][2:v][2:a]concat=n=3:v=1:a=1[outv][outa]; \
    [outa][3:a]amix=inputs=2:duration=first:weights=1 1:normalize=0[finalaudio]" \
    -map "[outv]" -map "[finalaudio]" -c:v libx264 -preset fast -crf 18 -c:a aac -b:a 320k "{Cookup.cookup_exports}/export/{final_directory.name}.mov"'''
    
    run_ffmpeg_and_update_db(combine_command, final_directory.name)

def main(rootdir: str) -> None:
    # Main function to process all folders in the import directory
    os.chdir(rootdir)
    import_folder = Path(rootdir) / 'import'
    if not import_folder.exists():
        print('Import folder not found!')
        sys.exit(1)

    dircheck(f'{rootdir}/export')

    for folder in listdir_nohidden(import_folder):
        process_folder(Path(folder), rootdir)

if __name__ == "__main__":
    query = input('json / process: ')
    if query == 'json':
        json_path = Path(input('Give the path to the folder: ').strip("'\""))
        write_json(json_path)
    elif query == 'process':
        inputdir = input('Input the root directory path: ').strip("'\"")
        main(inputdir)
    else:
        print('Invalid option!')