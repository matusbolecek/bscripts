from pathlib import Path
import os
import glob

def listdir_nohidden(path):
    return glob.glob(os.path.join(path, '*'))

dirlist = []
while True:
    userinput = input('Input the folder with the names ("x" to stop): ')
    if userinput == "x":
        break
    dirlist.append(userinput.strip("'\""))

files = []
for dirs in dirlist:
    for file in listdir_nohidden(dirs):
        files.append(Path(file).stem)

with open('names.txt', mode='a+', encoding='utf-8') as myfile:
    myfile.write("\n".join(files) + "\n")