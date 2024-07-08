from pathlib import Path
import random
import glob
import re
import subprocess
import os

def listdir_nohidden(path):
    return glob.glob(os.path.join(path, '*'))

# videos per one clip
video_count = 5

pack_name = input('What is the pack name? ')
viddir = input('Input the video directory path: ')
viddir = viddir.strip("'\"")

pack_path = Path(f'/Users/matusbolecek/BEATSTARS/Packs/{pack_name}')
finals_path = Path(f'/Users/matusbolecek/BEATSTARS/Packs/{pack_name}/vids')
if not pack_path.exists():
    print("Warning: the pack folder doesn't seem to exist")
    output_count = int(input('How many videos should be rendered? '))
else:
    output_count = 0
    for temps in listdir_nohidden(Path(f'/Users/matusbolecek/BEATSTARS/Packs/{pack_name}/temps')):
        output_count += 1
    
finals_path.mkdir(parents=True)

# main loop
video_list = []
for item in listdir_nohidden(viddir):
    video_list.append(item)

output_number = 1
for i in range(output_count):
    args = str('')
    for i in range(video_count):
        num = random.randint(0, len(video_list))
        os.chdir(finals_path)
        f = open("vidlist.txt", "a+") 
        f.write(f'file {video_list[num]}\n')
        f.close()

    render_ffmpeg = str(f'ffmpeg -f concat -safe 0  -i vidlist.txt -c copy "{finals_path}/{output_number}.mp4"')
    subprocess.run(render_ffmpeg, shell = True, executable="/bin/bash")
    output_number += 1
    os.remove('vidlist.txt')