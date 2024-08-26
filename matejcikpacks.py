import os
import subprocess
import random
from pathlib import Path
from typing import List, Tuple
import sqlite3
from fpdf import FPDF
from pypdf import PdfMerger
import re

from beatstars import bpm_convert
from beatstars_config import Beatpack, Management

def connect_to_database():
    conn = sqlite3.connect(Management.database_path_beats)
    conn.create_function("LOWER", 1, lambda x: x.lower() if x else None)
    return conn

def get_beat_from_database(cursor, name: str, bpm: int, key: str) -> Tuple:
    query = '''
    SELECT * FROM beats 
    WHERE LOWER(name) = LOWER(?) AND tempo = ? AND (LOWER(key) = LOWER(?) OR LOWER(key) = LOWER(?))
    '''
    cursor.execute(query, (name, bpm, key, key + " Minor"))
    result = cursor.fetchone()
    
    if result:
        print(f"Debug: Exact match found: {result}")
        print(f"Debug: Pack name type: {type(result[4])}, value: {result[4]}")
    
    if result is None:
        print(f"Debug: No exact match found for name='{name}', bpm={bpm}, key='{key}'")
        # Try a more lenient search
        query = '''
        SELECT * FROM beats 
        WHERE LOWER(name) = LOWER(?) AND (tempo = ? OR ABS(tempo - ?) <= 1)
        '''
        cursor.execute(query, (name, bpm, bpm))
        result = cursor.fetchone()
        if result:
            print(f"Debug: Found a close match: {result}")
            print(f"Debug: Pack name type: {type(result[4])}, value: {result[4]}")
        else:
            print("Debug: No close match found either.")
            
        # Print all beats with the same name for debugging
        cursor.execute("SELECT * FROM beats WHERE LOWER(name) = LOWER(?)", (name,))
        all_matches = cursor.fetchall()
        if all_matches:
            print(f"Debug: All beats with name '{name}':")
            for match in all_matches:
                print(match)
        else:
            print(f"Debug: No beats found with name '{name}'")
    
    return result

def update_beat_pack(cursor, beat_id: int, pack_name: str):
    cursor.execute('''
    UPDATE beats SET pack = ? WHERE id = ?
    ''', (str(pack_name), beat_id))

def update_beat_link(cursor, beat_id: int, link: str):
    cursor.execute('''
    UPDATE beats SET link = ? WHERE id = ?
    ''', (link, beat_id))

def add_new_beat(cursor, name: str, collaborators: str, key: str, tempo: int, link: str):
    cursor.execute('''
    INSERT INTO beats (name, collaborators, key, tempo, link)
    VALUES (?, ?, ?, ?, ?)
    ''', (name.title(), collaborators, key, tempo, link))
    return cursor.lastrowid

def extract_beat_info(filename: str) -> Tuple[str, str, int, str]:
    print(f"Parsing filename: {filename}")  # Debug print
    
    # Remove file extension
    name_without_extension = os.path.splitext(filename)[0]
    print(f"Name without extension: {name_without_extension}")  # Debug print
    
    # Split by ' - '
    parts = name_without_extension.split(' - ')
    print(f"Parts after splitting: {parts}")  # Debug print
    
    if len(parts) < 2:
        raise ValueError(f"Filename '{filename}' does not contain enough parts separated by ' - '")
    
    # Extract collaborators (if any)
    if '@' in parts[0]:
        collaborators = parts[0]
        name_parts = parts[1:]
    else:
        collaborators = '@matejcikbeats'
        name_parts = parts
    
    print(f"Collaborators: {collaborators}")  # Debug print
    print(f"Name parts: {name_parts}")  # Debug print
    
    # The last part should contain BPM and key
    bpm_key_part = name_parts[-1]
    
    # Use regular expressions to find BPM and key
    bpm_match = re.search(r'\d+', bpm_key_part)
    key_match = re.search(r'[A-G](?:#|b)?(?:maj|min)', bpm_key_part, re.IGNORECASE)
    
    if not bpm_match:
        raise ValueError(f"Could not extract BPM from '{bpm_key_part}'")
    if not key_match:
        raise ValueError(f"Could not extract key from '{bpm_key_part}'")
    
    bpm = int(bpm_match.group())
    key = key_match.group()
    
    # Extract the actual beat name (everything before BPM)
    name = bpm_key_part.split(str(bpm))[0].strip()
    
    print(f"Extracted name: {name}")  # Debug print
    print(f"Extracted BPM: {bpm}")  # Debug print
    print(f"Extracted key: {key}")  # Debug print
    
    return name, collaborators, bpm, key

def process_beat(cursor, file: Path, pack_name: str) -> Tuple:
    try:
        name, collaborators, bpm, key = extract_beat_info(file.name)
        print(f"Extracted info: name='{name}', collaborators='{collaborators}', bpm={bpm}, key='{key}'")
    except ValueError as e:
        print(f"Error processing {file.name}: {str(e)}")
        return None, False  # Return None instead of raising an exception

    if not name:
        print(f"Warning: Empty beat name extracted from '{file.name}'. Skipping this file.")
        return None, False  # Return None instead of raising an exception

    beat = get_beat_from_database(cursor, name, bpm, key)
    
    if beat:
        print(f"Debug: Beat found in database: {beat}")
        current_pack = beat[4] if isinstance(beat[4], str) else None
        if current_pack is None or current_pack.lower() == pack_name.lower():
            if beat[7] is None:  # Check if link is None
                link = input(f"Enter link for beat '{name}': ")
                update_beat_link(cursor, beat[0], link)
                beat = get_beat_from_database(cursor, name, bpm, key)  # Fetch updated beat
            update_beat_pack(cursor, beat[0], pack_name)
            print(f"Updated: {file.name} (added to pack: {pack_name})")
            return beat, True
        else:
            print(f"Skipped: {file.name} (already in different pack: {current_pack})")
            return beat, False
    else:
        print(f"Beat '{name}' not found in database. Please enter the following information:")
        link = input("Enter link: ")
        beat_id = add_new_beat(cursor, name, collaborators, key, bpm, link)
        update_beat_pack(cursor, beat_id, pack_name)
        return get_beat_from_database(cursor, name, bpm, key), True

def tag_and_copy_beat(input_file: Path, output_file: Path, bpm: int):
    tag_folder = Beatpack.resources_path / 'Tags'
    tag_list = [str(item) for item in tag_folder.iterdir() if item.is_file() and item.suffix.lower() in ('.wav', '.mp3')]
    if not tag_list:
        print('No valid audio tags found in Tag folder!')
        return

    try:
        # Time-stretch the tag
        chosen_tag = random.choice(tag_list)
        tagmpeg = f'ffmpeg -i "{chosen_tag}" -filter:a "atempo={(18 / bpm_convert(bpm, 12))}" newtag.wav'
        subprocess.run(tagmpeg, shell=True, executable="/bin/bash", check=True)

        # Mix the tag with the beat
        mp3mpeg = f'ffmpeg -i "{input_file}" -i "newtag.wav" -filter_complex amix=inputs=2:duration=longest:normalize=0 -ab 320k "{output_file}"'
        subprocess.run(mp3mpeg, shell=True, executable="/bin/bash", check=True)

        os.remove('newtag.wav')
        print(f"Successfully tagged and copied: {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error in ffmpeg processing: {e}")
    except Exception as e:
        print(f"Error in tag_and_copy_beat: {e}")

def generate_pdfs_and_merge(pack_name: str, beat_properties: list, output_folder: Path, resources_path: Path):
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

    # Generate tracklist PDF
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
        pdf.chapter_body(f'{track_nr}. "{pdf_props[0]}" - {pdf_props[1]} {pdf_props[2]}\n (prod. by {collab})')
        if pdf_props[4]:
            pdf.add_hyperlink(pdf_props[4], pdf_props[4])
        track_nr += 1
    tracklist_pdf = output_folder / 'list.pdf'
    pdf.output(str(tracklist_pdf))

    # Generate title PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(2.54, 2.54)
    pdf.set_font(family='Times', size=30)
    pdf.set_text_color(r=0, g=0, b=0)
    pdf.set_y(pdf.h / 2 - 15)
    pdf.cell(w=pdf.w - 25, txt=f'"{pack_name}" Beatpack Terms', align="C")
    title_pdf = output_folder / 'title.pdf'
    pdf.output(str(title_pdf))

    # Merge PDFs
    pdfs = [str(title_pdf), str(resources_path / 'terms.pdf'), str(tracklist_pdf)]
    merger = PdfMerger()
    for pdf in pdfs:
        merger.append(pdf)
    output_pdf = output_folder / f'{pack_name} Terms.pdf'
    merger.write(str(output_pdf))
    merger.close()

    # Remove temporary PDFs
    os.remove(str(title_pdf))
    os.remove(str(tracklist_pdf))

    return output_pdf

def create_thank_you_txt(pack_name: str, beat_count: int, output_folder: Path):
    thank_you_content = f"""Thank you for downloading the {pack_name} beat pack!
It contains {beat_count} high-quality beats to make hits with.

Make sure to read the terms before using the beats.

I am running bulk discounts (Buy 2 Get 1 Free or Buy 3 Get 2 Free) on my beatstore, so make sure to take advantage of them while purchasing leases.

Send me back what you make on my instagram @matejcikbeats.

Enjoy!

-matejcikbeats
instagram.com/matejcikbeats
matejcikbeats.beatstars.com
"""
    thank_you_file = output_folder / 'THANK YOU!.txt'
    with open(thank_you_file, 'w') as f:
        f.write(thank_you_content)

    return thank_you_file

def process_beatpack(pack_name: str, beat_properties: list, output_folder: Path, resources_path: Path):
    # Generate and merge PDFs
    merged_pdf = generate_pdfs_and_merge(pack_name, beat_properties, output_folder, resources_path)
    
    # Create THANK YOU.txt
    thank_you_file = create_thank_you_txt(pack_name, len(beat_properties), output_folder)
    
    print(f"Generated merged PDF: {merged_pdf}")
    print(f"Generated THANK YOU.txt: {thank_you_file}")

def main():
    conn = connect_to_database()
    cursor = conn.cursor()

    pack_name = input("Enter the name of the beatpack: ")
    input_folder = Path(input("Enter the input folder path: ").strip("'\""))
    output_folder = Path(input("Enter the output folder path: ").strip("'\""))
    output_folder.mkdir(parents=True, exist_ok=True)

    selected_beats = []
    beat_properties = []

    for file in input_folder.iterdir():
        if file.suffix.lower() in ('.mp3', '.wav'):
            try:
                print(f"\nProcessing file: {file.name}")
                beat, should_process = process_beat(cursor, file, pack_name)
                if should_process and beat is not None:
                    selected_beats.append(beat)
                    output_file = output_folder / file.name
                    try:
                        tag_and_copy_beat(file, output_file, beat[4])  # beat[4] is tempo
                        print(f"Processed and copied: {file.name}")
                        
                        # Create beat_properties string
                        beat_props = f"{beat[1]};{beat[4]};{beat[3]};{beat[2]};{beat[8] or ''}"
                        beat_properties.append(beat_props)
                    except Exception as e:
                        print(f"Error in tagging and copying {file.name}: {str(e)}")
                        print("Skipping this file and continuing with the next one.")
            except Exception as e:
                print(f"Error processing {file.name}: {str(e)}")
                print("Skipping this file and continuing with the next one.")

    conn.commit()

    if selected_beats:
        process_beatpack(pack_name, beat_properties, output_folder, Beatpack.resources_path)
        print(f"Processed {len(selected_beats)} beats for pack '{pack_name}'")
    else:
        print("No beats were processed for this pack.")

    conn.close()

if __name__ == "__main__":
    main()