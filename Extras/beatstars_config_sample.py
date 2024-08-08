# Rename to beatstars_config.py

from pathlib import Path

beatstars_folder = '/Volumes/wd/BEATSTARS'

class Beatpack:
    resources = Path('') # Path to resources folder
    packs_path = f'{beatstars_folder}/Packs'

class Typebeat:
    watermark = str('') # Path to watermark
    export_directory = str(f'{beatstars_folder}/Export')
    mp3_directory = str(f'{beatstars_folder}/Bounces')
    pictures = f'{beatstars_folder}/pics'

class Videopicker:
    packs_folder = f'{beatstars_folder}/Packs'
    video_folder = f'{beatstars_folder}/Cookups/!Materials/cut_clips/future' # Music video clips path

class Cookup:
    cookup_exports = f'{beatstars_folder}/Cookups'
    cookup_materials = f'{beatstars_folder}/Cookups/!Materials'
    lut_path = f'{beatstars_folder}/Cookups/!Materials/luts'

class Management:
    database_path_beats = f'' # Path to the database for beats
    database_path_loops = f''

class Publisher:
    resources_path = f'' # Path to the publisher data
    dropbox_token = ''