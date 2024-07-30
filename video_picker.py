from pathlib import Path
import random
import glob
import re
import subprocess
import os

from beatstars_config import Videopicker, beatstars_folder

def listdir_nohidden(path):
    return glob.glob(os.path.join(path, '*'))

pack_name = input('What is the pack name? ')
viddir = Videopicker.video_folder.strip("'\"")
outputs = int(input('How many videos should be rendered? '))
pack_path = Path(f'{Videopicker.packs_folder}/{pack_name}')
finals_path = Path(f'{Videopicker.packs_folder}/{pack_name}/vids')
finals_path.mkdir(parents=True)

def generator(video_directory, output_count, render_path, video_count):
    video_list = []
    for item in listdir_nohidden(video_directory):
        video_list.append(item)

    output_number = 1
    for i in range(output_count):
        args = str('')
        for i in range(video_count):
            num = random.randint(0, len(video_list))
            os.chdir(render_path)
            f = open("vidlist.txt", "a+") 
            f.write(f'file {video_list[num]}\n')
            f.close()

        render_ffmpeg = str(f'ffmpeg -f concat -safe 0  -i vidlist.txt -c copy "{render_path}/{output_number}.mp4"')
        subprocess.run(render_ffmpeg, shell = True, executable="/bin/bash")
        output_number += 1
        os.remove('vidlist.txt')

generator(viddir, outputs, finals_path, 5)