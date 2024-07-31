from pathlib import Path
import random
import subprocess
import os
import json
import sys
import fnmatch

from beatstars_config import Cookup, beatstars_folder
from video_picker import generator
from beatstars import listdir_nohidden, bpm_convert, dircheck, silence_read

def write_json(path):
    f = open(f'{path}/props.json', 'a+')
    f.write('{\n')
    f.write('\t"video_bpm": " ",\n')
    f.write('\t"cookup_start": " ",\n')
    f.write('\t"cookup_end": " ",\n')
    f.write('\t"loop_text": " ",\n')
    f.write('\t"intro_length_bars": "12",\n')
    f.write('\t"preview_length_bars": "24"\n')    
    f.write('}')
    f.close()

# Folder management
def video(rootdir):
    os.chdir(rootdir)
    import_folder = Path(f'{rootdir}/import')
    if not import_folder.exists():
        print('Import folder not found!')
        sys.exit()

    dircheck(f'{rootdir}/export')

    for folders in listdir_nohidden(f'{rootdir}/import'):
        folder_path = Path(folders)
        file_list = []

        # Checks to see if the folder has all files
        json_in_folder = 0
        for file in folder_path.iterdir():
            if fnmatch.fnmatch(file.name, '*.mov') or fnmatch.fnmatch(file.name, '*.mp4'):
                file_list.append(file)
            if fnmatch.fnmatch(file.name, 'props.json'):
                json_in_folder = 1

        # Read props
        with open(f"{folder_path}/props.json", "r") as f:
            props = json.load(f)
        if len(file_list) != 2 or json_in_folder == 0:
            print(f'Error in folder {os.path.basename(folders)}! Exactly 3 files must be in every folder.')
            sys.exit()
        final_directory = f'{rootdir}/export/{os.path.basename(folders)}'
        os.mkdir(final_directory)
        file_list.sort()

        # Silence reading
        audio_start = silence_read(file_list[1])
        ffmpeg = f'ffmpeg -i "{file_list[1]}" -ss {audio_start + bpm_convert(props["video_bpm"], 4)} -to {audio_start + bpm_convert(props["video_bpm"], (4 + int(props["intro_length_bars"])))} -vn -acodec copy "{final_directory}/audio.aac"'
        subprocess.run(ffmpeg, shell = True, executable="/bin/bash")
        
        # Tag picking and stretching
        if int(props["intro_length_bars"]) == 12:
            tag_list = [f'{Cookup.cookup_materials}/tags/alttag_12bar.wav', f'{Cookup.cookup_materials}/tags/tag_12bar.wav']
            ffmpeg = str(f'ffmpeg -i "{random.choice(tag_list)}" -filter:a "atempo={(18 / bpm_convert(props["video_bpm"], 12))}" "{final_directory}/tag.wav"')
        else:
            ffmpeg = str(f'ffmpeg -i {Cookup.cookup_materials}/tags/tag_xbar.wav "{final_directory}/tag.wav"')
        subprocess.run(ffmpeg, shell = True, executable="/bin/bash")

        # Intro
        generator(f'{Cookup.cookup_materials}/cut_clips/future', 1, final_directory, 8)
        ffmpeg = f'ffmpeg -i "{final_directory}/1.mp4" -i "{Cookup.cookup_materials}/overlay.mov" -i "{Cookup.cookup_materials}/intro.png" -i "{final_directory}/audio.aac" -i "{final_directory}/tag.wav" -filter_complex "\
        [0:v]boxblur=40,scale=2560x1440,setsar=1[bg];\
        [0:v]scale=1440:1440:force_original_aspect_ratio=decrease[fg];\
        [bg][fg]overlay=x=(W-w)/2:y=(H-h)/2[base];\
        [base][1:v]blend=all_mode=softlight:all_opacity=0.3[softlight];\
        [softlight][2:v]overlay=(W-w)/2:(H-h)/2[v];\
        [3:a][4:a]amix=inputs=2:duration=longest:normalize=0[a]\
        " -map "[v]" -map "[a]" -c:v h264 -c:a aac -to {bpm_convert(props["video_bpm"], 12)} "{final_directory}/first.mov"'
        subprocess.run(ffmpeg, shell = True, executable="/bin/bash")
        os.remove(f'{final_directory}/tag.wav')
        os.remove(f'{final_directory}/1.mp4')
        os.remove(f'{final_directory}/audio.aac')

        # Second video
        ffmpeg = f"""
        ffmpeg -ss {props["cookup_start"]} -to {props["cookup_end"]} -i "{file_list[0]}" \
        -filter_complex "[0:v]drawtext=fontfile='{Cookup.cookup_materials}/font.ttf': \
        text='{props["loop_text"]}': \
        x=(w-text_w)/2: \
        y=h-(text_h*2): \
        fontsize=64: \
        fontcolor=white: \
        alpha='if(lt(t,5),0,if(lt(t,6),(t-5)/1,if(lt(t,14),1,if(lt(t,15),(1-(t-14))/1,0))))' \
        [v]" \
        -map "[v]" -map 0:a -c:v h264 -c:a aac "{final_directory}/second.mov"
        """
        subprocess.run(ffmpeg, shell=True, executable="/bin/bash")

        # Preview video
        lut_list = []
        for file in Path(Cookup.lut_path).iterdir():
            if fnmatch.fnmatch(file.name, '*.cube'):
                lut_list.append(Path(file))
        ffmpeg = f'ffmpeg -ss {audio_start} -to {audio_start + bpm_convert(props["video_bpm"], int(props["preview_length_bars"]))} -i "{file_list[1]}" -i "{Cookup.cookup_materials}/outro.png" -filter_complex "[0:v]lut3d="{random.choice(lut_list)}"[video];[video][1:v]overlay=0:0" -c:v h264 -c:a copy "{final_directory}/third.mov"'
        subprocess.run(ffmpeg, shell=True, executable="/bin/bash")

        # Final video
        os.chdir(final_directory)
        input_files = ["first.mov", "second.mov", "third.mov"]
        remuxed_files = ["remuxed1.mov", "remuxed2.mov", "remuxed3.mov"]
        
        for input_file, remuxed_file in zip(input_files, remuxed_files):
            ffmpeg = f'ffmpeg -i {input_file} -c copy -fflags +genpts {remuxed_file}'
            subprocess.run(ffmpeg, shell = True, executable="/bin/bash")

        with open('vidlist.txt', 'w') as f:
            for remuxed_file in remuxed_files:
                f.write(f"file '{remuxed_file}'\n")

        ffmpeg = str(f'ffmpeg -f concat -safe 0  -i vidlist.txt -c copy "{os.path.basename(folders)}.mov"')
        subprocess.run(ffmpeg, shell = True, executable="/bin/bash")
        
        input_files.extend(remuxed_files)
        for files in input_files:
            os.remove(files)
        os.remove('vidlist.txt')

if __name__ == "__main__":
    inputdir = input('Input the root directory path: ').strip("'\"")
    video(inputdir)
    # write_json('/Users/matusbolecek/BEATSTARS/! Scripts')