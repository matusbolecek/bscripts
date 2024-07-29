from pathlib import Path
import subprocess

# Sets
from beatstars_config import Beatstars
watermark = Beatstars.watermark
dir = Beatstars.export_directory
mp3dir = Beatstars.mp3_directory

artist = input('nardo / future / lone: ')
if artist == "nardo" or artist == "future" or artist == "lone":
    print('Good!')
else:
    print('Not a valid option!')
    sys.exit()

# Inputs
water = str(input('Watermark? Yes/No: '))
video = str(input('Video filename: '))
audio = str(input('Audio filename: '))
export = (f"'{dir}/{Path(audio).stem}.mp4'")
export2 = (f"'{mp3dir}/{Path(audio).stem} ({artist}) .mp3'")


string = str(f'ffmpeg -threads 0 -framerate 24 -loop 1 -i {video} -i {watermark} -i {audio} -filter_complex "[0:v]scale=-2:1080:flags=lanczos,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black[base]; [1:v]scale=1920:-1:flags=lanczos[overlay]; [base][overlay]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2" -c:a aac -c:v h264_videotoolbox -shortest {export}')
audio2 = str(f'ffmpeg -i {audio} {export2}')

subprocess.run(string, shell = True, executable="/bin/bash")
subprocess.run(audio2, shell = True, executable="/bin/bash")