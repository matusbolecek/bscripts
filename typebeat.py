import fnmatch
from pathlib import Path
import sys
import os
import subprocess
import shutil
import random
import glob
import re

from beatstars_config import Typebeat, beatstars_folder
from beatstars import listdir_nohidden

# Inputs
artists = ['nardo', 'future', 'southside', 'lone']
artist = input(f"{' / '.join(artists)}: ")
if artist in artists:
    picdir = str(f'{Typebeat.pictures}/{artist}')
else:
    print('Not a valid option!')
    sys.exit()

rootdir = input('Input the root directory path: ').strip("'\"")

# Check if there is enough pictures
count1 = 0
count2 = 0
for path in listdir_nohidden(picdir):
    if os.path.isfile(os.path.join(picdir, path)):
        count1 += 1
for path in listdir_nohidden(rootdir):
    if os.path.isdir(os.path.join(rootdir, path)):
        count2 += 1
if count1 < count2:
    print(f'There is not enough pictures in the specified folder! {abs(count1-count2)} pictures missing!')
    sys.exit()

# Main
num = 1
for folder in listdir_nohidden(rootdir):
    folder_path = Path(folder)

    for file in folder_path.iterdir():
        if fnmatch.fnmatch(file.name, '*Current.wav'):
            os.remove(file)

    # Set master file
    for file in folder_path.iterdir():
        if fnmatch.fnmatch(file.name, '*Master.wav'):
            master = file.name
            master_path = file

    # Zip 
    print(f'Zipping file {num}/{count2}')
    os.chdir(folder)
    os.mkdir('Stems')       
    excluded_string = "Master.wav"
    files = os.listdir(folder_path)
    stemsfolder = str(f'{folder_path}/Stems')
    for file in files:
        if excluded_string not in file:
            file_path = os.path.join(folder_path, file)
            shutil.move(file_path, stemsfolder)

    subprocess.run('7z a -tzip -r stems.zip Stems/ -x!*.DS_Store -x!__MACOSX*', shell=True, stdout = subprocess.DEVNULL)
    shutil.rmtree(stemsfolder)
    zipname = master.replace('_Master.wav', '_Stems.zip')
    os.rename('stems.zip', zipname)
    print('Done!')

    picture = random.choice(os.listdir(picdir))
    picture_path = str(f'{picdir}/{picture}')

    # Render
    print(f'Rendering file {num}/{count2}')
    export_name = (f"'{Typebeat.export_directory}/{Path(master).stem}.mp4'")
    ffmpeg=str(f'ffmpeg -threads 0 -framerate 24 -loop 1 -i "{picture_path}" -i "{Typebeat.watermark}" -i "{master_path}" -filter_complex "[0:v]scale=-2:1080:flags=lanczos,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black[base]; [1:v]scale=1920:-1:flags=lanczos[overlay]; [base][overlay]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2" -c:a aac -c:v h264_videotoolbox -shortest {export_name}')
    subprocess.run(ffmpeg, shell = True, executable="/bin/bash") # , stdout = subprocess.DEVNULL, stderr = subprocess.STDOUT

    shutil.move(picture_path, folder_path)
    print('Done!')

    print(f'Rendering MP3 {num}/{count2}')
    mp3_name = (f"'{Typebeat.mp3_directory}/{Path(master).stem} ({artist}).mp3'")
    mp3mpeg = str(f'ffmpeg -i "{master_path}" -ab 320k {mp3_name}')
    subprocess.run(mp3mpeg, shell = True, executable="/bin/bash", stdout = subprocess.DEVNULL, stderr = subprocess.STDOUT)
    print('Done!')

    num += 1