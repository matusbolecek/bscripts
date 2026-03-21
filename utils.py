from pathlib import Path
import random
import glob
import re
import subprocess
import os


def listdir_nohidden(path: Path) -> list[Path]:
    return [p for p in path.iterdir() if not p.name.startswith(".")]


def bpm_convert(bpm: int, bars: int) -> float:
    return (60 / bpm) * 4 * bars


def dircheck(dir: Path) -> None:
    dir = Path(dir)
    if not dir.exists():
        dir.mkdir(parents=True)


def silence_read(file_path: Path) -> float:
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
    stdout_output, stderr_output = process.communicate()

    for line in stderr_output.splitlines():
        match = re.search(pattern, line)
        if match:
            silence_end = float(match.group(1))
            break

    return silence_end


def ffmpeg_run(command: str) -> None:
    subprocess.run(command, shell=True, executable="/bin/bash")

