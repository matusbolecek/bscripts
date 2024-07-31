from pathlib import Path
import random
import glob
import re
import subprocess
import os

def listdir_nohidden(path):
    return glob.glob(os.path.join(path, '*'))

def bpm_convert(bpm, bars):
    return float((1/(int(bpm) / 60)) * 4 * bars)

def dircheck(dir):
   dir = Path(dir)
   if not dir.exists():
    dir.mkdir(parents=True)

def silence_read(file_path):
    ffmpeg_command = ["ffmpeg", "-i", f'{file_path}', "-vn", "-af", "silencedetect=n=-50dB:d=1", "-f", "null", "-"]
    process = subprocess.Popen(ffmpeg_command, stderr=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)
    silence_end = None
    pattern = r'silence_end:\s*(\d+\.\d+)'
    stdout_output, stderr_output = process.communicate()

    for line in stderr_output.splitlines():
        match = re.search(pattern, line)
        if match:
            silence_end = float(match.group(1))
            break
    return silence_end

def ffmpeg_run(command):
    subprocess.run(command, shell = True, executable="/bin/bash")