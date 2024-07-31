from pathlib import Path
import random
import glob
import re
import subprocess
import os

file_path = '/Volumes/wd/test/import/bulletproof/2024-07-29 23-10-28.mov'

ffmpeg_command = ["ffmpeg", "-i", fr'{file_path}', "-af", "silencedetect=n=-50dB:d=1", "-f", "null", "-"]
process = subprocess.Popen(ffmpeg_command, stderr=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)
silence_end = None
pattern = r'silence_end:\s*(\d+\.\d+)'
stdout_output, stderr_output = process.communicate()

for line in stderr_output.splitlines():
    match = re.search(pattern, line)
    if match:
        silence_end = float(match.group(1))
        break

print(silence_end)