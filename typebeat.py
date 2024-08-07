import fnmatch
from pathlib import Path
import sys
import os
import subprocess
import shutil
import random

from beatstars_config import Typebeat, beatstars_folder
from beatstars import listdir_nohidden
from beat_management import BeatManager

def get_valid_artist():
    artists = ['nardo', 'future', 'southside', 'lone']
    while True:
        artist = input(f"Choose an artist ({' / '.join(artists)}): ")
        if artist in artists:
            return artist, f'{Typebeat.pictures}/{artist}'
        print('Not a valid option! Please try again.')

def count_files(directory, condition):
    return sum(1 for path in listdir_nohidden(directory) if condition(os.path.join(directory, path)))

def check_picture_count(pic_dir, root_dir):
    pic_count = count_files(pic_dir, os.path.isfile)
    folder_count = count_files(root_dir, os.path.isdir)
    if pic_count < folder_count:
        print(f'Not enough pictures in the specified folder! {folder_count - pic_count} pictures missing!')
        sys.exit(1)

def process_folder(folder_path, picdir, artist, num, total, beatlist):
    folder_path = Path(folder_path)
    
    # Remove current.wav files
    for file in folder_path.glob('*Current.wav'):
        file.unlink()

    # Find master file
    master_files = list(folder_path.glob('*Master.wav'))
    if not master_files:
        print(f"No master file found in {folder_path}")
        return
    master_file = master_files[0]

    # Zip stems
    print(f'Zipping file {num}/{total}')
    stems_folder = folder_path / 'Stems'
    stems_folder.mkdir(exist_ok=True)
    for file in folder_path.iterdir():
        if 'Master.wav' not in file.name and file.is_file():
            shutil.move(str(file), str(stems_folder))

    subprocess.run(['7z', 'a', '-tzip', '-r', 'stems.zip', 'Stems/', '-x!*.DS_Store', '-x!__MACOSX*'], 
                   cwd=str(folder_path), stdout=subprocess.DEVNULL)
    shutil.rmtree(stems_folder)
    zip_name = master_file.stem.replace('_Master', '_Stems') + '.zip'
    (folder_path / 'stems.zip').rename(folder_path / zip_name)
    print('Zipping done!')

    # Render video
    picture = random.choice(os.listdir(picdir))
    picture_path = os.path.join(picdir, picture)
    print(f'Rendering video {num}/{total}')
    export_name = os.path.join(Typebeat.export_directory, f"{master_file.stem}.mp4")
    ffmpeg_cmd = [
        'ffmpeg', '-threads', '0', '-framerate', '24', '-loop', '1',
        '-i', picture_path, '-i', str(Typebeat.watermark), '-i', str(master_file),
        '-filter_complex', "[0:v]scale=-2:1080:flags=lanczos,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black[base]; [1:v]scale=1920:-1:flags=lanczos[overlay]; [base][overlay]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2",
        '-c:a', 'aac', '-c:v', 'h264_videotoolbox', '-shortest', export_name
    ]
    subprocess.run(ffmpeg_cmd, check=True)
    shutil.move(picture_path, str(folder_path))
    print('Video rendering done!')

    # Render MP3
    print(f'Rendering MP3 {num}/{total}')
    mp3_name = os.path.join(Typebeat.mp3_directory, f"{master_file.stem} ({artist}).mp3")
    subprocess.run(['ffmpeg', '-i', str(master_file), '-ab', '320k', mp3_name], 
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    print('MP3 rendering done!')

    # Write filename to global filename list
    beatlist.append(master_file.stem)

def data_write(beatlist):
    manager = BeatManager()
    manager.add_beats_from_filenames(beatlist)
    manager.close()

if __name__ == "__main__":
    artist, picdir = get_valid_artist()
    beat_names = []
    
    # Improved input handling for paths with escaped spaces
    rootdir = input('Input the root directory path: ')
    rootdir = rootdir.strip("'\"")  # Remove any surrounding quotes
    rootdir = rootdir.replace("\\ ", " ")  # Replace escaped spaces with actual spaces
    rootdir = os.path.expanduser(rootdir)  # Expand user directory if present (e.g., ~)
    rootdir = os.path.abspath(rootdir)  # Convert to absolute path
    
    if not os.path.exists(rootdir):
        print(f"The directory '{rootdir}' does not exist.")
        sys.exit(1)

    check_picture_count(picdir, rootdir)

    total_folders = sum(1 for _ in listdir_nohidden(rootdir))
    for num, folder in enumerate(listdir_nohidden(rootdir), 1):
        process_folder(os.path.join(rootdir, folder), picdir, artist, num, total_folders, beat_names)

    data_write(beat_names)