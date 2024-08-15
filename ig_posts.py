import os
import subprocess
import re
from beatstars import bpm_convert

def clean_path(path):
    return path.strip().strip("'\"")

def get_input_folder():
    return clean_path(input("Enter the path to the folder containing audio files and a picture: "))

def get_export_folder():
    return clean_path(input("Enter the path to the export folder: "))

def get_video_type():
    while True:
        video_type = input("Enter the video type (beat or loop): ").lower()
        if video_type in ['beat', 'loop']:
            return video_type
        print("Invalid input. Please enter 'beat' or 'loop'.")

def create_video(audio_file, image_file, output_file, duration):
    command = [
        'ffmpeg',
        '-loop', '1',
        '-i', image_file,
        '-i', audio_file,
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-tune', 'stillimage',
        '-c:a', 'aac',
        '-b:a', '320k',
        '-pix_fmt', 'yuv420p',
        '-shortest',
        '-t', str(duration),
        '-vf', 'scale=1080:1080:force_original_aspect_ratio=decrease,pad=1080:1080:(ow-iw)/2:(oh-ih)/2',
        '-threads', '0',
        output_file
    ]
    subprocess.run(command, check=True)

def parse_loop_filename(filename):
    parts = os.path.splitext(filename)[0].split()
    for part in reversed(parts):
        if part.isdigit():
            return int(part)
    return None

def get_tempo_from_filename(filename):
    tempo = parse_loop_filename(filename)
    if tempo is None:
        print(f"Could not determine tempo for file: {filename}")
        while True:
            try:
                tempo = int(input("Please enter the tempo manually: "))
                return tempo
            except ValueError:
                print("Invalid input. Please enter a number.")
    return tempo

def main():
    input_folder = get_input_folder()
    export_folder = get_export_folder()
    video_type = get_video_type()

    if not os.path.exists(input_folder):
        print(f"Error: The input folder '{input_folder}' does not exist.")
        return

    if not os.path.exists(export_folder):
        os.makedirs(export_folder)

    image_file = None
    audio_files = []

    for file in os.listdir(input_folder):
        if file.lower().endswith(('.png', '.jpg', '.jpeg')):
            image_file = os.path.join(input_folder, file)
        elif file.lower().endswith(('.wav', '.mp3')):
            audio_files.append(os.path.join(input_folder, file))

    if not image_file:
        print("No image file found in the input folder.")
        return

    if not audio_files:
        print("No audio files found in the input folder.")
        return

    for audio_file in audio_files:
        output_file = os.path.join(export_folder, f"{os.path.splitext(os.path.basename(audio_file))[0]}.mp4")

        if video_type == 'beat':
            duration = 58
        else:  # loop
            tempo = get_tempo_from_filename(os.path.basename(audio_file))
            duration = bpm_convert(tempo, 24)

        try:
            create_video(audio_file, image_file, output_file, duration)
            print(f"Created video: {output_file}")
        except subprocess.CalledProcessError:
            print(f"Error creating video for {audio_file}")

if __name__ == "__main__":
    main()