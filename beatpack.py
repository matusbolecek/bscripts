from pathlib import Path  
import re
import subprocess
import time
from fpdf import FPDF
from pypdf import PdfMerger
import os
import glob

def listdir_nohidden(path):
    return glob.glob(os.path.join(path, '*'))

# Pack name and paths
pack_name = input('What is the pack name?')
finals_path = Path(f'/Users/matusbolecek/BEATSTARS/Packs/{pack_name}/Final')
if not finals_path.exists():
    finals_path.mkdir(parents=True)
res_path = Path(f'/Users/matusbolecek/BEATSTARS/Packs/{pack_name}/Resources')
if not res_path.exists():
    res_path.mkdir()
pack_path = Path(f'/Users/matusbolecek/BEATSTARS/Packs/{pack_name}')
if not pack_path.exists():
    pack_path.mkdir()
resources = Path('/Users/matusbolecek/BEATSTARS/! Scripts/Resources')

# Input dataset
beat_properties = []
beat_paths = []
beat_number = 1
sortdir = input('Input the SORTED beat directory path: ')
sortdir = sortdir.strip("'\"")
unsortdir = input('Input the UNSORTED beat directory path: ')
unsortdir = unsortdir.strip("'\"")
lastdir = input('Input the BONUS beat directory path ("x" if none): ')
lastdir = lastdir.strip("'\"")

# Sorting
video_beat_count = 0
temp_list = []
for item in listdir_nohidden(sortdir):
    temp_list.append(item)
    temp_list.sort()
    video_beat_count += 1

for item in listdir_nohidden(unsortdir):
    temp_list.append(item)

if lastdir != "x":
    for item in listdir_nohidden(lastdir):
        temp_list.append(item)

# Props input
for beat in temp_list:
    input_properties = input(f'Paste the properties of the {beat}. beat: ')

    filename = Path(beat).name
    bpm_extract = [int(s) for s in re.findall(r'\b\d+\b', filename)]
    if len(bpm_extract) == 0:
        bpm = str('- BPM')
    else:
        if len(bpm_extract) == 1:
            bpm = int(bpm_extract[0])
        else:
            for items in bpm_extract:
                if items < 90 or items > 180:
                    bpm_extract.remove(items)
            if len(bpm_extract) == 1:
                bpm = int(bpm_extract[0])
            else:
                bpm = max(bpm_extract)
    
    bpm_import = tuple(input_properties.split(';'))
    if int(bpm_import[2]) == int(bpm):
        beat_properties.append(input_properties)
        beat_paths.append(beat)
        beat_number += 1        
    else:
        check_input = input(f'The BPM of the selected track ({bpm}) does not match the track properties ({bpm_import[2]}). Do you want to procceed anyway? (Y/N)')
        if check_input == 'Y':
            beat_properties.append(input_properties)
            beat_paths.append(beat)
            beat_number += 1
        else:
            input_properties = input(f'Paste the correct properties of the {beat}. beat: ')
            beat_properties.append(input_properties)
            beat_paths.append(beat)
            beat_number += 1

# Finals folder output
track_nr = 1
for paths in beat_paths:
    current_props = str(beat_properties[track_nr-1])
    props = tuple(current_props.split(';'))
    if props[3] == '-':
        collab = str('@matejcikbeats')
    else:
        collab = str(f'@matejcikbeats x {props[3]}')
    new_name = str(f'{track_nr}. {props[0]} - {props[2]}BPM {props[1]} {collab}.mp3')
    mp3mpeg = str(f'ffmpeg -i "{paths}" -ab 320k "{finals_path}/{new_name}"')
    subprocess.run(mp3mpeg, shell = True, executable="/bin/bash")
    track_nr += 1

# Temps folder output
temp_nr = 1
time_list = []
for temps in beat_paths:
    if temp_nr > video_beat_count:
        break
    bpm_import = tuple(beat_properties[temp_nr-1].split(';'))
    temp_time = float((1/(int(bpm_import[2]) / 60))*160)
    time_list.append(temp_time)
    if Path(temps).suffix[1:] == 'mp3':
        mp3mpeg = str(f'ffmpeg -to {temp_time} -i "{temps}" -af "silenceremove=start_periods=1:start_duration=0:start_threshold=-50dB" -ab 320k "{res_path}/{temp_nr}.wav"')
    else:
        mp3mpeg = str(f'ffmpeg -to {temp_time} -i "{temps}" -ab 320k "{res_path}/{temp_nr}.wav"')
    subprocess.run(mp3mpeg, shell = True, executable="/bin/bash")
    temp_nr += 1

# Description generator
f = open(f"{pack_path}/desc.txt", "a+")
total_time = 0
time_number = 0
for times in time_list:
    desc_import = tuple(beat_properties[time_number].split(';'))
    f.write(f"{time.strftime('%M:%S', time.gmtime(total_time))} {desc_import[0]} {desc_import[2]} {desc_import[1]}")
    f.write('\n')
    time_number += 1
    total_time += times
f.close()

# .srt generator
f = open(f"{pack_path}/{pack_name}.srt", "a+")
sub_starttime = 0
sub_endtime = 0
time_number = 0
for times in time_list:
    sub_endtime += times
    desc_import = tuple(beat_properties[time_number].split(';'))
    f.write(str(int(2 * (time_number + 1) - 1)))
    f.write('\n')
    f.write(f"{time.strftime('%H:%M:%S:000', time.gmtime(sub_starttime))} --> {time.strftime('%H:%M:%S:000', time.gmtime(sub_endtime - 10))}\n")
    f.write(str(f'"{desc_import[0]}" - {desc_import[2]} {desc_import[1]}\n'))
    if desc_import[3] == '-':
        collab = str('@matejcikbeats')
    else:
        collab = str(f'@matejcikbeats x {desc_import[3]}')
    f.write(f'prod. by {collab}\n')
    f.write('\n')
    f.write(str(int(2 * (time_number + 1))))
    f.write('\n')
    f.write(str(f"{time.strftime('%H:%M:%S:000', time.gmtime(sub_endtime - 10))} --> {time.strftime('%H:%M:%S:000', time.gmtime(sub_endtime))}\n"))
    f.write(f'Download this beat and {len(beat_properties) - 1} others for FREE!\n')
    f.write('Link in the Description \n\n')
    time_number += 1
    sub_starttime += times
f.close()

# PDF Generator
class PDF(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font('Times', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no() + 2}', 0, 0, 'C')

    def chapter_title(self, title):
        self.set_font('Times', 'B', 12)
        self.cell(0, 10, title, 0, 1, 'L')
        self.ln(10)

    def chapter_body(self, body):
        self.set_font('Times', '', 12)
        self.multi_cell(0, 5, body)
        self.ln()

    def add_hyperlink(self, text, url):
        self.set_font('Times', 'U', 12)
        self.set_text_color(0, 0, 255)
        self.cell(0, 0, text, link=url)
        self.set_text_color(0, 0, 0)
        self.ln(10)

pdf = PDF()
pdf.add_page()
pdf.chapter_title(f'{pack_name} tracklist')
track_nr = 1
for props in beat_properties:
    pdf_props = tuple(props.split(';'))
    if pdf_props[3] == '-':
        collab = str('@matejcikbeats')
    else:
        collab = str(f'@matejcikbeats x {pdf_props[3]}')
    pdf.chapter_body(f'{track_nr}. "{pdf_props[0]}" - {pdf_props[2]} {pdf_props[1]}\n (prod. by {collab})')
    pdf.add_hyperlink(pdf_props[4], pdf_props[4])
    track_nr += 1
pdf.output(f'{pack_path}/list.pdf')

pdf = FPDF()
pdf.add_page()
pdf.set_margins(2.54, 2.54)
pdf.set_font(family='Times', size=30)
pdf.set_text_color(r=0, g=0, b=0)
pdf.set_y(pdf.h / 2 - 15)
pdf.cell(w=pdf.w - 25, txt=f'"{pack_name}" Beatpack Terms', align="C")
pdf.output(f'{pack_path}/title.pdf')

# merge
pdfs = [f'{pack_path}/title.pdf', f'{resources}/terms.pdf', f'{pack_path}/list.pdf']
merger = PdfMerger()
for pdf in pdfs:
    merger.append(pdf)
merger.write(f'{finals_path}/{pack_name} Terms.pdf')
merger.close()

os.remove(f'{pack_path}/title.pdf')
os.remove(f'{pack_path}/list.pdf')

# thank you .txt generator
f = open(f"{finals_path}/THANK_YOU!.txt", "a+")
f.write(f'Thank you for downloading the {pack_name} beat pack! \n')
f.write(f'It contains {len(beat_properties)} high-quality beats to make hits with. \n')
f.write('Make sure to read the terms before using the beats. \n')
f.write('I am running bulk discounts (Buy 2 Get 1 Free or Buy 3 Get 2 Free) on my beatstore, so make sure to take advantage of them while purchasing leases. \n')
f.write('Send me back what you make on my instagram @matejcikbeats. \n')
f.write('\n')
f.write('Enjoy! \n')
f.write('\n')
f.write('-matejcikbeats \n')
f.write('instagram.com/matejcikbeats \n')
f.write('matejcikbeats.beatstars.com \n')
f.close()

# Excel list generator
f = open(f"{pack_path}/excel.txt", "a+")
for properties in beat_properties:
    f.write(properties)
    f.write('\n')
f.close()