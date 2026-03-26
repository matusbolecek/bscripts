from pathlib import Path
import os
import glob
import sys

from utils import listdir_nohidden

folder_path = Path(input("Input the directory: ").strip("'\""))
keyword = str(os.path.basename(folder_path))[:-1]
txt_path = Path(input("Input the names txt file: ").strip("'\""))
keep_attributes = input(
    "Do you want to keep the original file name as part of the output? (Y/n)"
)
if keep_attributes not in ["Y", "y", "N", "n"] and keep_attributes != "":
    print("Wrong input!")
    sys.exit()

files = []
for file in listdir_nohidden(folder_path):
    files.append(file)

names = []
with open(txt_path, "r+") as f:
    names = f.readlines()
    f.seek(0)
    f.truncate(0)

if len(names) < len(files):
    print("More names needed!")
    sys.exit()

os.chdir(folder_path)
for file in files:
    newname = str(names[0]).strip("\n")
    if keep_attributes == "y" or keep_attributes == "Y" or keep_attributes == "":
        finalname = str(
            f"{keyword} - {newname} - {Path(file).stem} @matejcikbeats{Path(file).suffix}"
        )
    else:
        finalname = str(f"{keyword} - {newname} @matejcikbeats{Path(file).suffix}")
    os.rename(f"{file}", finalname)
    names.pop(0)

f = open(txt_path, "r+")
for name in names:
    f.write(name)
f.close()
