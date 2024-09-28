from typebeat import *

def recycle(folder_path, picdir, viddir, artist, num, total, beatlist):
    folder_path = Path(folder_path)

    # Find master file
    master_files = list(folder_path.glob('*.wav'))
    if not master_files:
        print(f"No master file found in {folder_path}")
        return
    master_file = master_files[0]

    # Create export folder for this beat
    export_folder = Path(Typebeat.export_directory) / artist / master_file.stem
    export_folder.mkdir(parents=True, exist_ok=True)

    # Render video
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            # Select and copy random picture to the folder_path
            pictures = [f for f in os.listdir(picdir) if not f.startswith('.')]
            if not pictures:
                print(f"No pictures found in {picdir}")
                return
            picture = random.choice(pictures)
            picture_path = os.path.join(picdir, picture)
            dest_picture_path = folder_path / picture
            shutil.copy2(picture_path, dest_picture_path)

            # Select random video with minimum duration
            video_path = select_random_video(viddir)
            if not video_path:
                print(f"Failed to find a suitable video. Skipping this folder.")
                return

            print(f'Rendering video {num}/{total} (Attempt {attempt + 1})')
            export_name = export_folder / f"{master_file.stem}.mp4"
            
            # Get audio duration
            ffprobe_cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(master_file)]
            duration = float(subprocess.check_output(ffprobe_cmd).decode('utf-8').strip())
            
            create_looping_video(video_path, str(export_name), str(master_file), str(Typebeat.watermark_black), duration)
            print('Video rendering done!')

            # Create thumbnail
            thumbnail_path = export_folder / f"{master_file.stem}_thumbnail.jpg"
            create_thumbnail(str(dest_picture_path), str(Typebeat.watermark_black), str(thumbnail_path))
            print('Thumbnail created!')

            # Move picture to archive
            archive_dir = Path(picdir).parent / 'archive' / artist
            archive_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(picture_path, archive_dir / picture)

            break  # If we get here, the video was rendered successfully

        except subprocess.CalledProcessError as e:
            print(f"Error during attempt {attempt + 1}: {str(e)}")
            if attempt == max_attempts - 1:
                print(f"Failed to render video after {max_attempts} attempts. Skipping this folder.")
                return
            else:
                print("Retrying with a different video and picture...")

    # Write filename to global filename list
    beatlist.append(master_file.stem)

if __name__ == "__main__":
    artist, picdir, viddir = get_valid_artist()
    beat_names = []

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
        recycle(os.path.join(rootdir, folder), picdir, viddir, artist, num, total_folders, beat_names)