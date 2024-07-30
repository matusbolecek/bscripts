import os
import subprocess
import random

video_path = '/Users/matusbolecek/Movies/social\ script/2024-07-06\ 13-04-38.mp4'
picture_path = '/Users/matusbolecek/Movies/social\ script/test.png'
huewheel = random.randint(-360, 360)

ffmpeg = str(
    f'ffmpeg -i {video_path} -i {picture_path} -filter_complex \
"[0:v]scale=-1:1440,perspective=0:0:W+250:-250:0:H:W+250:H+250[v]; \
 [1:v][v]overlay=-325:480,hue=h={huewheel}" \
-c:v libx264 -crf 23 -preset medium output.mp4'
)

subprocess.run(ffmpeg, shell = True, executable="/bin/bash")