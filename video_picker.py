import random
import subprocess
from pathlib import Path
from typing import Union, List

from beatstars import listdir_nohidden
from beatstars_config import Videopicker, beatstars_folder


def generator(
    video_directory: Union[str, Path],
    output_count: int,
    render_path: Path,
    video_count: int,
) -> None:
    video_list = [Path(item) for item in listdir_nohidden(video_directory)]

    for output_number in range(1, output_count + 1):
        video_list_file = render_path / "vidlist.txt"
        output_file = render_path / f"{output_number}.mp4"

        # Create video list file
        selected_videos = random.sample(video_list, video_count)
        with video_list_file.open("w") as f:
            for video in selected_videos:
                f.write(f"file {video}\n")

        # Render video
        render_ffmpeg = (
            f"ffmpeg -f concat -safe 0 -i {video_list_file} -c copy {output_file}"
        )
        try:
            subprocess.run(
                render_ffmpeg, shell=True, check=True, executable="/bin/bash"
            )
        except subprocess.CalledProcessError as e:
            print(f"Error rendering video {output_number}: {e}")

        # Clean up
        video_list_file.unlink()


if __name__ == "__main__":
    pack_name = input("What is the pack name? ")
    viddir = Path(Videopicker.video_folder.strip("'\""))
    outputs = int(input("How many videos should be rendered? "))

    pack_path = Path(Videopicker.packs_folder) / pack_name
    finals_path = pack_path / "vids"
    finals_path.mkdir(parents=True, exist_ok=True)

    generator(viddir, outputs, finals_path, 5)

