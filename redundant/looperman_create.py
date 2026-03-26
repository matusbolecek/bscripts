import os
import subprocess
import sys


def process_wav_files(input_folder):
    input_folder = input_folder.strip("'\"")
    finished_folder = os.path.join(input_folder, "finished")
    os.makedirs(finished_folder, exist_ok=True)

    wav_files = [f for f in os.listdir(input_folder) if f.lower().endswith(".wav")]

    for filename in wav_files:
        input_path = os.path.join(input_folder, filename)
        output_path = os.path.join(finished_folder, filename)

        if "finished" in input_path or "uploaded" in input_path:
            continue

        ffmpeg_command = ["ffmpeg", "-i", input_path, "-ar", "44100", "-y", output_path]

        try:
            subprocess.run(ffmpeg_command, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            print(f"Error processing {filename}: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        input_folder = sys.argv[1]
    else:
        input_folder = input("Enter the path to the input folder: ").strip()

    process_wav_files(input_folder)

