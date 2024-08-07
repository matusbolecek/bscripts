import sqlite3
from dataclasses import dataclass
from typing import Optional, List

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

class BeatManager:
    def __init__(self, db_name=Management.database_path_beats):
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
         link TEXT)
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
        self.conn.commit()

    def add_beat(self, beat: Beat):
        self.cursor.execute('''
        INSERT INTO beats (name, collaborators, key, tempo, pack, tutorial_made, social_media_video_made, link)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (beat.name, beat.collaborators, beat.key, beat.tempo, beat.pack, 
              beat.tutorial_made, beat.social_media_video_made, beat.link))
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

        beat = Beat(name=name, collaborators=collaborators, key=key, tempo=tempo, pack=pack, link=link)
        self.add_beat(beat)
        print("Beat added successfully.")

    def add_beat_by_filename(self):
        filename = input("Enter filename: ")
        beat = self.parse_filename(filename)
        self.add_beat(beat)
        print("Beat added successfully.")

    def close(self):
        self.conn.close()

def main():
    manager = BeatManager()
    
    print("Welcome to the Beat Management System!")
    print("Available commands: list, add_properties, add_filename, remove, exit")

    while True:
        command = input("Enter command: ").lower()

        if command == "exit":
            manager.close()
            print("Exiting Beat Management System. Goodbye!")
            break
        elif command == "list":
            manager.list_beats()
        elif command == "add_properties":
            manager.add_beat_by_properties()
        elif command == "add_filename":
            manager.add_beat_by_filename()
        elif command == "remove":
            beat_id = int(input("Enter the ID of the beat to remove: "))
            manager.remove_beat(beat_id)
            print(f"Beat with ID {beat_id} removed successfully.")
        else:
            print("Invalid command. Please try again.")

if __name__ == "__main__":
    main()