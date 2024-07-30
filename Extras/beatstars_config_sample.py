# Rename to beatstars_config.py

from pathlib import Path

beatstars_folder = '/Volumes/wd/BEATSTARS'

class Beatpack:
    resources = Path('') # Path to resources folder
    packs_path = f'{beatstars_folder}/Packs'

class Beatstars:
    watermark = str('') # Path to watermark
    export_directory = str(f'{beatstars_folder}/Export')
    mp3_directory = str(f'{beatstars_folder}/Bounces')
    pictures = f'{beatstars_folder}/pics'

class Videopicker:
    packs_folder = f'{beatstars_folder}/Packs'
    video_folder = '' # Music video clips path