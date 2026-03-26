from pathlib import Path
import re
import subprocess
import os
import sys


def listdir_nohidden(path: Path) -> list[Path]:
    return [p for p in path.iterdir() if not p.name.startswith(".")]


def dircheck(dir: Path) -> None:
    dir = Path(dir)
    if not dir.exists():
        dir.mkdir(parents=True)


def count_files(directory, condition):
    return sum(
        1
        for path in listdir_nohidden(directory)
        if condition(os.path.join(directory, path))
    )


def bpm_convert(bpm: int, bars: int) -> float:
    return (60 / bpm) * 4 * bars


class FFcomms:
    def __init__(self, watermark_black):
        self.watermark_black = watermark_black

    @staticmethod
    def silence_read(file_path: Path) -> float | None:
        ffmpeg_command = [
            "ffmpeg",
            "-i",
            f"{file_path}",
            "-vn",
            "-af",
            "silencedetect=n=-50dB:d=1",
            "-f",
            "null",
            "-",
        ]
        process = subprocess.Popen(
            ffmpeg_command,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            universal_newlines=True,
        )
        silence_end = None
        pattern = r"silence_end:\s*(\d+\.\d+)"
        _, stderr_output = process.communicate()

        for line in stderr_output.splitlines():
            match = re.search(pattern, line)
            if match:
                silence_end = float(match.group(1))
                break

        return silence_end

    @staticmethod
    def get_duration(video_path) -> float:
        ffprobe_cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ]

        try:
            return float(subprocess.check_output(ffprobe_cmd).decode("utf-8").strip())

        except subprocess.CalledProcessError:
            return 0

    def looping(self, input_path, output_path, audio_file, duration):
        return [
            "ffmpeg",
            "-stream_loop",
            "-1",
            "-i",
            input_path,
            "-i",
            audio_file,
            "-i",
            self.watermark_black,
            "-filter_complex",
            "[0:v]trim=start_frame=1,scale=-2:1080:flags=lanczos,setsar=1[v]; \
             [v][0:v]concat=n=2:v=1[looped]; \
             [looped]scale=-2:1080:flags=lanczos,setsar=1[scaled_video]; \
             [2:v][scaled_video]overlay=(W-w)/2:(H-h)/2:format=auto,format=yuv420p[final]",
            "-map",
            "[final]",
            "-map",
            "1:a",
            "-shortest",
            "-c:v",
            "libx264",
            "-preset",
            "fast" "-c:a",
            "aac",
            "-t",
            str(duration),
            output_path,
        ]

    def thumbnail(self, picture_file, thumbnail_file):
        return [
            "ffmpeg",
            "-i",
            self.watermark_black,
            "-i",
            picture_file,
            "-filter_complex",
            "[1:v]scale=-2:1080:flags=lanczos[pic];[0:v][pic]overlay=(W-w)/2:(H-h)/2",
            "-frames:v",
            "1",
            thumbnail_file,
        ]

    def mp3(self, master_file, mp3_name):
        return ["ffmpeg", "-i", str(master_file), "-ab", "320k", mp3_name]


class UserPath:
    def __init__(self):
        self.path = None

    def _check_exist(self, folder):
        if not os.path.exists(folder):
            print(f"The directory '{folder}' does not exist.")
            return False
        return True

    def _clean_path(self):
        self.path = str(self.path).strip("'\"")
        self.path = self.path.replace("\\ ", " ")
        self.path = os.path.expanduser(self.path)
        self.path = os.path.abspath(self.path)

    def read_while(self):
        while not self.path:
            folder = input("Input the root directory path: ")
            if self._check_exist(folder):
                self.path = folder
                self._clean_path()

    def read_once(self):
        folder = input("Input the root directory path: ")
        if self._check_exist(folder):
            self.path = folder
            self._clean_path()
        else:
            sys.exit(1)
