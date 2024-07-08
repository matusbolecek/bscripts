import os
import sys
from pathlib import Path

rootdir = input('Input the root directory path: ')
rootdir = rootdir.strip("'\"")
os.chdir(rootdir)

beat_list = Path("beat_list.txt")
if not beat_list.exists():
    print('Beat list does not exist!')
    sys.exit()

with open('beat_list.txt') as beatlist:
    for line in beatlist:
        beat_properties = tuple(line.split(';'))
        os.mkdir(f'{beat_properties[0]}')
        f = open(f'{beat_properties[0]}/props.txt', "a+")
        f.write(line)
        f.close()