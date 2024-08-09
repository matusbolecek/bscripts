import sqlite3
from dataclasses import dataclass
from typing import Optional, List
import os

from beatstars_config import Management

@dataclass
class Beat:
    name: str
    collaborators: str
    key: str
    tempo: int
    pack: Optional[str] = None
    tutorial_made: bool = False
    social_media_video_made: bool = False
    link: Optional[str] = None
    typebeat_uploaded: bool = False

class BeatManager:
    def __init__(self, db_name):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_table()
        self.update_schema()

    def create_table(self):
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS beats
        (id INTEGER PRIMARY KEY,
         name TEXT,
         collaborators TEXT,
         key TEXT,
         tempo INTEGER,
         pack TEXT,
         tutorial_made BOOLEAN,
         social_media_video_made BOOLEAN,
         link TEXT,
         typebeat_uploaded BOOLEAN)
        ''')
        self.conn.commit()

    def update_schema(self):
        columns = [row[1] for row in self.cursor.execute("PRAGMA table_info(beats)")]
        if 'pack' not in columns:
            self.cursor.execute('ALTER TABLE beats ADD COLUMN pack TEXT')
        if 'tutorial_made' not in columns:
            self.cursor.execute('ALTER TABLE beats ADD COLUMN tutorial_made BOOLEAN DEFAULT 0')
        if 'social_media_video_made' not in columns:
            self.cursor.execute('ALTER TABLE beats ADD COLUMN social_media_video_made BOOLEAN DEFAULT 0')
        if 'link' not in columns:
            self.cursor.execute('ALTER TABLE beats ADD COLUMN link TEXT')
        if 'typebeat_uploaded' not in columns:
            self.cursor.execute('ALTER TABLE beats ADD COLUMN typebeat_uploaded BOOLEAN DEFAULT 0')
        self.conn.commit()

    def add_beat(self, beat: Beat):
        self.cursor.execute('''
        INSERT INTO beats (name, collaborators, key, tempo, pack, tutorial_made, social_media_video_made, link, typebeat_uploaded)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (beat.name, beat.collaborators, beat.key, beat.tempo, beat.pack, 
              beat.tutorial_made, beat.social_media_video_made, beat.link, beat.typebeat_uploaded))
        self.conn.commit()

    def remove_beat(self, beat_id):
        self.cursor.execute('DELETE FROM beats WHERE id = ?', (beat_id,))
        self.conn.commit()

    def get_beat(self, beat_id):
        self.cursor.execute('SELECT * FROM beats WHERE id = ?', (beat_id,))
        return self.cursor.fetchone()

    def update_tutorial_flag(self, beat_id, tutorial_made=True):
        self.cursor.execute('UPDATE beats SET tutorial_made = ? WHERE id = ?', (tutorial_made, beat_id))
        self.conn.commit()

    def update_social_media_video_flag(self, beat_id, social_media_video_made=True):
        self.cursor.execute('UPDATE beats SET social_media_video_made = ? WHERE id = ?', 
                            (social_media_video_made, beat_id))
        self.conn.commit()

    def update_pack(self, beat_id, pack_name):
        self.cursor.execute('UPDATE beats SET pack = ? WHERE id = ?', (pack_name, beat_id))
        self.conn.commit()

    def update_link(self, beat_id, link):
        self.cursor.execute('UPDATE beats SET link = ? WHERE id = ?', (link, beat_id))
        self.conn.commit()

    def update_typebeat_uploaded(self, beat_id, typebeat_uploaded=True):
        self.cursor.execute('UPDATE beats SET typebeat_uploaded = ? WHERE id = ?', (typebeat_uploaded, beat_id))
        self.conn.commit()

    def get_all_beats(self):
        self.cursor.execute('SELECT * FROM beats')
        return self.cursor.fetchall()

    def get_beats_without_links(self):
        self.cursor.execute('SELECT id, name FROM beats WHERE link IS NULL OR link = ""')
        return self.cursor.fetchall()

    def add_links_interactively(self):
        beats_without_links = self.get_beats_without_links()
        
        if not beats_without_links:
            print("All beats already have links.")
            return

        print("Adding links to beats. Type '!exit' to stop the process at any time.")
        
        for beat_id, beat_name in beats_without_links:
            link = input(f"Enter link for beat '{beat_name}' (ID: {beat_id}): ")
            
            if link.lower() == '!exit':
                print("Link addition process terminated.")
                break
            
            self.update_link(beat_id, link)
            print(f"Link added for beat '{beat_name}'.")

        print("Link addition process completed.")

    @staticmethod
    def convert_key(short_key: str) -> str:
        note = short_key[0].upper()
        if len(short_key) > 1 and short_key[1] == '#':
            note += '#'
            mode = short_key[2:]
        else:
            mode = short_key[1:]

        if mode.lower() == 'min':
            return f"{note} Minor"
        elif mode.lower() == 'maj':
            return f"{note} Major"
        else:
            return short_key  # Return original if not recognized

    @classmethod
    def parse_filename(cls, filename: str) -> Beat:
        parts = filename.split(' - ')
        collaborators_part = parts[0]
        rest = parts[1]

        if 'x' in collaborators_part:
            collaborators = collaborators_part.replace('@', '').replace(' x ', ', ')
        else:
            collaborators = collaborators_part.replace('@', '')

        name_tempo_key = rest.rsplit(' ', 2)
        name = name_tempo_key[0].title()
        tempo = int(name_tempo_key[1])
        short_key = name_tempo_key[2].split('_')[0]
        key = cls.convert_key(short_key)

        return Beat(name=name, collaborators=collaborators, key=key, tempo=tempo)

    def add_beats_from_filenames(self, filenames: List[str]):
        for filename in filenames:
            beat = self.parse_filename(filename)
            self.add_beat(beat)
        print(f"Added {len(filenames)} beats to the database.")

    def list_beats(self):
        all_beats = self.get_all_beats()
        for beat in all_beats:
            print(beat)

    def add_beat_by_properties(self):
        name = input("Enter beat name: ")
        collaborators = input("Enter collaborators (or press Enter for Matejcikbeats): ")
        if not collaborators:
            collaborators = "Matejcikbeats"
        key = input("Enter key: ")
        tempo = int(input("Enter BPM: "))
        pack = input("Enter pack (or press Enter for None): ")
        if not pack:
            pack = None
        link = input("Enter link (or press Enter for None): ")
        if not link:
            link = None
        typebeat_uploaded = input("Is this beat uploaded to Typebeat? (y/n): ").lower() == 'y'

        beat = Beat(name=name, collaborators=collaborators, key=key, tempo=tempo, 
                    pack=pack, link=link, typebeat_uploaded=typebeat_uploaded)
        self.add_beat(beat)
        print("Beat added successfully.")

    def add_beat_by_filename(self):
        filename = input("Enter filename: ")
        beat = self.parse_filename(filename)
        self.add_beat(beat)
        print("Beat added successfully.")

    def close(self):
        self.conn.close()

    def search_beats(self, query, search_by='name', has_pack=False):
        if search_by == 'id':
            self.cursor.execute('SELECT * FROM beats WHERE id = ?', (query,))
        elif search_by == 'name':
            self.cursor.execute('SELECT * FROM beats WHERE LOWER(name) LIKE ?', (f'%{query.lower()}%',))
        elif search_by == 'pack':
            if has_pack:
                self.cursor.execute('SELECT * FROM beats WHERE pack IS NOT NULL AND pack != ""')
            else:
                self.cursor.execute('SELECT * FROM beats WHERE LOWER(pack) LIKE ?', (f'%{query.lower()}%',))
        else:
            raise ValueError("Invalid search_by parameter")
        
        return self.cursor.fetchall()

    @staticmethod
    def parse_loop_filename(filename: str) -> Beat:
        # Remove file extension
        name_parts = filename.rsplit('.', 1)[0].split()
        
        # Extract collaborators
        collaborators = "@matejcikbeats"
        if 'x' in name_parts:
            x_index = name_parts.index('x')
            collaborators_parts = name_parts[x_index-1:]
            collaborators = ', '.join([part.strip('@') for part in collaborators_parts if part != 'x'])
            name_parts = name_parts[:x_index-1]
        elif name_parts[-1].startswith('@'):
            collaborators = name_parts[-1]
            name_parts = name_parts[:-1]
        
        # Extract tempo and key
        tempo = int(name_parts[-2])
        key = name_parts[-1]
        
        # Extract name
        name = ' '.join(name_parts[:-2])
        
        return Beat(name=name, collaborators=collaborators, key=key, tempo=tempo)

    def add_loops_from_filenames(self, filenames: List[str]):
        for filename in filenames:
            loop = self.parse_loop_filename(filename)
            self.add_beat(loop)  # Assuming you're using the same add_beat method for loops
        print(f"Added {len(filenames)} loops to the database.")

    def add_beats_from_file(self, file_path: str):
        with open(file_path, 'r') as file:
            filenames = file.read().splitlines()
        
        added_count = 0
        for filename in filenames:
            if filename.strip():  # Skip empty lines
                if self.conn.database == Management.database_path_beats:
                    beat = self.parse_filename(filename)
                else:
                    beat = self.parse_loop_filename(filename)
                self.add_beat(beat)
                added_count += 1
        
        print(f"Added {added_count} items to the database.")

def main():
    beat_manager = BeatManager(Management.database_path_beats)
    loop_manager = BeatManager(Management.database_path_loops)
    
    print("Welcome to the Beat and Loop Management System!")
    print("Available commands: b* (for beats), l* (for loops), exit")
    
    while True:
        command = input("Enter command (beats/loops/exit): ").lower()
        if command == "exit":
            beat_manager.close()
            loop_manager.close()
            print("Exiting Beat and Loop Management System. Goodbye!")
            break
        elif command.startswith('b'):
            manage_items(beat_manager, "Beat")
        elif command.startswith('l'):
            manage_items(loop_manager, "Loop")
        else:
            print("Invalid command. Please try again.")

def manage_items(manager, item_type):
    print(f"{item_type} Management")
    print("Available commands: list, add_properties, add_filename, add_file_list, remove, add_links, search, update_typebeat, back")

    while True:
        command = input(f"Enter {item_type.lower()} command: ").lower()

        if command == "back":
            break
        elif command == "list":
            manager.list_beats()
        elif command == "add_properties":
            manager.add_beat_by_properties()
        elif command == "add_filename":
            if item_type == "Beat":
                manager.add_beat_by_filename()
            else:
                filename = input("Enter loop filename: ")
                manager.add_loops_from_filenames([filename])
        elif command == "add_file_list":
            file_path = input("Enter the path to the file containing the list of filenames: ")
            if os.path.exists(file_path):
                manager.add_beats_from_file(file_path)
            else:
                print("File not found. Please check the path and try again.")
        elif command == "add_links":
            manager.add_links_interactively()
        elif command == "remove":
            item_id = int(input(f"Enter the ID of the {item_type.lower()} to remove: "))
            manager.remove_beat(item_id)
            print(f"{item_type} with ID {item_id} removed successfully.")
        elif command == "search":
            query = input("Enter search query: ")
            search_by = input("Search by (name/id/pack) [default: name]: ").lower() or 'name'
            
            if search_by == 'pack':
                has_pack = input(f"Search for {item_type.lower()}s with any pack? (y/n): ").lower() == 'y'
            else:
                has_pack = False

            results = manager.search_beats(query, search_by, has_pack)
            
            if results:
                print("Search results:")
                for item in results:
                    print(item)
            else:
                print(f"No {item_type.lower()}s found matching that criteria.")
        elif command == "update_typebeat":
            item_id = int(input(f"Enter the ID of the {item_type.lower()} to update: "))
            typebeat_uploaded = input("Has this beat been uploaded to Typebeat? (y/n): ").lower() == 'y'
            manager.update_typebeat_uploaded(item_id, typebeat_uploaded)
            print(f"{item_type} with ID {item_id} updated successfully.")
        else:
            print("Invalid command. Please try again.")

if __name__ == "__main__":
    main()