import os
import subprocess
import re
import random
from pathlib import Path
import sys
import glob
import fnmatch

def listdir_nohidden(path):
    return glob.glob(os.path.join(path, '*'))

# Root directory input
rootdir = input('Input the root directory path: ')
rootdir = rootdir.strip("'\"")

video_folder = Path(f'{rootdir}/videos')
resource_folder = Path(f'{rootdir}/resources')

if not video_folder.exists():
    print('Video folder does not exist!')
    sys.exit()
elif not resource_folder.exists():
    print('Resource folder does not exist!')
    sys.exit()    

# Resource list
pics = []
for resource in listdir_nohidden(resource_folder):
    pics.append(resource)

# Video folders
os.chdir(rootdir)
for folder in listdir_nohidden(video_folder):
    folder_path = Path(folder)

    for file in folder_path.iterdir():
        if fnmatch.fnmatch(file.name, '*.mp4'):
            video_path = file

    f = open(f"{folder_path}/props.txt", "r")
    beat_properties = tuple(f.readline().split(';'))
    f.close()

    # silence count
    ffmpeg_temp = str(f'ffmpeg -i "{video_path}" -ab 320k "social_temp.mp3"')
    subprocess.run(ffmpeg_temp, shell = True, executable="/bin/bash")
    ffmpeg_command = ["ffmpeg", "-i", "social_temp.mp3", "-af", "silencedetect=n=-50dB:d=1", "-f", "null", "-"]
    process = subprocess.Popen(ffmpeg_command, stderr=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)
    silence_end = None
    pattern = r'silence_end:\s*(\d+\.\d+)'
    stdout_output, stderr_output = process.communicate()

    for line in stderr_output.splitlines():
        match = re.search(pattern, line)
        if match:
            silence_end = float(match.group(1))
            break

    os.remove("social_temp.mp3")

    bpm = beat_properties[2]
    beat_time = float((1/(int(bpm) / 60))*96)
    intro_delay = float((1/(int(bpm) / 60))*16)
    huewheel = random.randint(-360, 360)

    for picture_path in pics:
        ffmpeg = str(
            f'ffmpeg -ss {silence_end + intro_delay - 0.1} -to {beat_time + silence_end} -i "{video_path}" -i "{picture_path}" -filter_complex \
        "[0:v]scale=-1:1440,perspective=0:0:W+250:-250:0:H:W+250:H+250,hue=h={huewheel}[v]; \
        [1:v][v]overlay=-325:480" \
        -c:v libx264 -crf 17 -preset slow "{beat_properties[0]}_temp.mp4"'
        )

        subprocess.run(ffmpeg, shell = True, executable="/bin/bash")

        ffmpeg_fin = str(f'ffmpeg -ss 0.1 -i "{beat_properties[0]}_temp.mp4" -c copy "{folder_path}/{beat_properties[0]}_{Path(picture_path).name}.mp4"')
        subprocess.run(ffmpeg_fin, shell = True, executable="/bin/bash")
        os.remove(f'{beat_properties[0]}_temp.mp4')
        os.remove(f"{folder_path}/props.txt")
        os.remove(f"{video_path}")