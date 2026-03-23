import sqlite3
from dataclasses import dataclass
from typing import Optional, List
import os
from pathlib import Path

from config import DBConfig

# this has to be implemented !!!
# if config not set in the constructor, it will just run a method that works on it (or fails - up for consideration)
# need config.prod_name, which returns the default prod name
# need config.db_beats, config.db_loops, which return the database beat paths

# parse filename most likely needs checks, as there is user input handled


@dataclass
class Beat:
    name: str
    collaborators: str
    key: str
    tempo: int
    pack: Optional[str] = None
    link: Optional[str] = None


class BeatManager:
    def __init__(self, db: Path):
        self.conn = sqlite3.connect(db)
        self.cursor = self.conn.cursor()
        self.create_table()
        self.config = DBConfig()

    def create_table(self):
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS beats
        (id INTEGER PRIMARY KEY,
         name TEXT,
         collaborators TEXT,
         key TEXT,
         tempo INTEGER,
         pack TEXT,
         link TEXT,
        """)
        self.conn.commit()

    def beat_exists(self, name: str) -> bool:
        self.cursor.execute("SELECT COUNT(*) FROM beats WHERE name = ?", (name,))
        count = self.cursor.fetchone()[0]
        return count > 0

    def add_beat(self, beat: Beat):
        if self.beat_exists(beat.name):
            print(
                f"Warning: A beat with the name '{beat.name}' already exists in the database."
            )
            user_choice = input("Do you want to add this beat anyway? (y/N): ").lower()
            if user_choice != "y":
                print("Beat not added.")
                return

        self.cursor.execute(
            """
        INSERT INTO beats (name, collaborators, key, tempo, pack, tutorial_made, social_media_video_made, link, typebeat_uploaded)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                beat.name,
                beat.collaborators,
                beat.key,
                beat.tempo,
                beat.pack,
                beat.link,
            ),
        )
        self.conn.commit()
        print(f"Beat '{beat.name}' added successfully.")

    def remove_beat(self, beat_id_or_range):
        if isinstance(beat_id_or_range, int):
            self.cursor.execute("DELETE FROM beats WHERE id = ?", (beat_id_or_range,))

        elif isinstance(beat_id_or_range, tuple) and len(beat_id_or_range) == 2:
            start, end = beat_id_or_range
            self.cursor.execute(
                "DELETE FROM beats WHERE id BETWEEN ? AND ?", (start, end)
            )

        else:
            raise ValueError(
                "Invalid input. Expected an integer ID or a tuple of (start, end) IDs."
            )
        self.conn.commit()

    def get_beat(self, beat_id):
        self.cursor.execute("SELECT * FROM beats WHERE id = ?", (beat_id,))
        return self.cursor.fetchone()

    def update_pack(self, beat_id, pack_name):
        self.cursor.execute(
            "UPDATE beats SET pack = ? WHERE id = ?", (pack_name, beat_id)
        )
        self.conn.commit()

    def update_link(self, beat_id, link):
        self.cursor.execute("UPDATE beats SET link = ? WHERE id = ?", (link, beat_id))
        self.conn.commit()

    def get_all_beats(self):
        self.cursor.execute("SELECT * FROM beats")
        return self.cursor.fetchall()

    def get_beats_without_links(self):
        self.cursor.execute(
            'SELECT id, name FROM beats WHERE link IS NULL OR link = ""'
        )
        return self.cursor.fetchall()

    def add_links_interactively(self):
        beats_without_links = self.get_beats_without_links()

        if not beats_without_links:
            print("All beats already have links.")
            return

        print(
            "Adding links to beats. Type '!exit' to stop the process, or '!skip' to skip a beat."
        )

        for beat_id, beat_name in beats_without_links:
            while True:
                link = input(f"Enter link for beat '{beat_name}' (ID: {beat_id}): ")

                if link.lower() == "!exit":
                    print("Link addition process terminated.")
                    return
                elif link.lower() == "!skip":
                    print(f"Skipped beat '{beat_name}'.")
                    break
                elif link.strip():
                    self.update_link(beat_id, link)
                    print(f"Link added for beat '{beat_name}'.")
                    break
                else:
                    print("Please enter a valid link, '!skip', or '!exit'.")

        print("Link addition process completed.")

    @staticmethod
    def convert_key(short_key: str) -> str:
        note = short_key[0].upper()
        if len(short_key) > 1 and short_key[1] == "#":
            note += "#"
            mode = short_key[2:]
        else:
            mode = short_key[1:]

        if mode.lower() == "min":
            return f"{note} Minor"
        elif mode.lower() == "maj":
            return f"{note} Major"
        else:
            return short_key  # Return original if not recognized

    @classmethod
    def parse_filename(cls, filename: str) -> Beat:
        parts = filename.split(" - ")
        collaborators_part = parts[0]
        rest = parts[1]

        if "x" in collaborators_part:
            collaborators = collaborators_part.replace("@", "").replace(" x ", ", ")
        else:
            collaborators = collaborators_part.replace("@", "")

        name_tempo_key = rest.rsplit(" ", 2)
        name = name_tempo_key[0].title()
        tempo = int(name_tempo_key[1])
        short_key = name_tempo_key[2].split("_")[0]
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

        collaborators = input(
            f"Enter collaborators (or press Enter for {self.config.prodname}): "
        )
        if not collaborators:
            collaborators = self.config.prodname

        key = input("Enter key: ")
        tempo = int(input("Enter BPM: "))

        pack = input("Enter pack (or press Enter for None): ")
        if not pack:
            pack = None

        link = input("Enter link (or press Enter for None): ")
        if not link:
            link = None

        beat = Beat(
            name=name,
            collaborators=collaborators,
            key=key,
            tempo=tempo,
            pack=pack,
            link=link,
        )
        self.add_beat(beat)
        print("Beat added successfully.")

    def add_beat_by_filename(self):
        filename = input("Enter filename: ")
        beat = self.parse_filename(filename)
        self.add_beat(beat)
        print("Beat added successfully.")  # maybe check if this can not break

    def close(self):
        self.conn.close()

    def search_beats(self, query, search_by="name", has_pack=False):
        match search_by:
            case "id":
                self.cursor.execute("SELECT * FROM beats WHERE id = ?", (query,))
            case "name":
                self.cursor.execute(
                    "SELECT * FROM beats WHERE LOWER(name) LIKE ?",
                    (f"%{query.lower()}%",),
                )
            case "pack":
                if has_pack:
                    self.cursor.execute(
                        'SELECT * FROM beats WHERE pack IS NOT NULL AND pack != ""'
                    )
                else:
                    self.cursor.execute(
                        "SELECT * FROM beats WHERE LOWER(pack) LIKE ?",
                        (f"%{query.lower()}%",),
                    )
            case _:
                raise ValueError("Invalid search_by parameter")

        return self.cursor.fetchall()

    def parse_loop_filename(self, filename: str) -> Beat:
        parts = filename.rsplit(".", 1)[0].split()

        # Extract key (always the last part before prodname or collaborators)
        key_index = next(
            i for i in range(len(parts) - 1, -1, -1) if parts[i].lower().endswith("min")
        )
        key = parts[key_index]

        # Extract tempo (always before the key)
        tempo = int(parts[key_index - 1])

        # Extract collaborators
        collaborators = self.config.prodname
        if "x" in parts:
            x_index = parts.index("x")
            collaborators = ", ".join(
                [
                    part.strip("@")
                    for part in parts[x_index:]
                    if part != "x" and not part.isdigit() and part != key
                ]
            )

        # Extract name (everything before tempo)
        name = " ".join(parts[: key_index - 1])

        return Beat(name=name, collaborators=collaborators, key=key, tempo=tempo)

    def add_loops_from_filenames(self, filenames: List[str]):
        added_count = 0
        for filename in filenames:
            try:
                loop = self.parse_loop_filename(filename)
                self.add_beat(loop)
                added_count += 1
            except Exception as e:
                print(f"Error processing file '{filename}': {str(e)}")
                print(f"Parsed parts: {filename.rsplit('.', 1)[0].split()}")
        print(f"Added {added_count} loops to the database.")

    def add_beats_from_file(self, file_path: str, item_type: str):
        with open(file_path, "r") as file:
            filenames = file.read().splitlines()

        if item_type.lower() == "loop":
            self.add_loops_from_filenames(filenames)
        else:
            self.add_beats_from_filenames(filenames)


def main():
    cfg = DBConfig()
    beat_manager = BeatManager(cfg.db_beats)
    loop_manager = BeatManager(cfg.db_loops)

    print("Welcome to the Beat and Loop Management System!")
    print("Available commands: b* (for beats), l* (for loops), exit")

    while True:
        command = input("Enter command (beats/loops/exit): ").lower()

        if command == "exit":
            beat_manager.close()
            loop_manager.close()
            print("Exiting Beat and Loop Management System. Goodbye!")
            break

        elif command.startswith("b"):
            manage_items(beat_manager, "Beat")

        elif command.startswith("l"):
            manage_items(loop_manager, "Loop")

        else:
            print("Invalid command. Please try again.")


def manage_items(manager, item_type):
    print(f"{item_type} Management")
    print(
        "Available commands:" "list,",
        "add_properties,",
        "add_filename," "add_file_list,",
        "remove,",
        "add_links,",
        "search,",
        "update_typebeat,",
        "back",
    )

    while True:
        command = input(f"Enter {item_type.lower()} command: ").lower()

        match command:
            case "back":
                break

            case "list":
                manager.list_beats()

            case "add_properties":
                manager.add_beat_by_properties()

            case "add_filename":
                if item_type == "Beat":
                    manager.add_beat_by_filename()
                else:
                    filename = input("Enter loop filename: ")
                    manager.add_loops_from_filenames([filename])

            case "add_file_list":
                file_path = input(
                    "Enter the path to the file containing the list of filenames: "
                )

                if os.path.exists(file_path):
                    manager.add_beats_from_file(file_path, item_type)
                else:
                    print("File not found. Please check the path and try again.")

            case "add_links":
                manager.add_links_interactively()

            case "remove":
                item_id_input = input(
                    f"Enter the ID or ID range (e.g., 10-20) of the {item_type.lower()}(s) to remove: "
                )

                try:
                    if "-" in item_id_input:
                        start, end = map(int, item_id_input.split("-"))
                        manager.remove_beat((start, end))
                        print(
                            f"{item_type}s with IDs from {start} to {end} removed successfully."
                        )

                    else:
                        item_id = int(item_id_input)
                        manager.remove_beat(item_id)
                        print(f"{item_type} with ID {item_id} removed successfully.")

                except ValueError as e:
                    print(f"Error: {str(e)}. Please enter a valid ID or ID range.")

            case "search":
                query = input("Enter search query: ")
                search_by = (
                    input("Search by (name/id/pack) [default: name]: ").lower()
                    or "name"
                )

                if search_by == "pack":
                    has_pack = (
                        input(
                            f"Search for {item_type.lower()}s with any pack? (y/n): "
                        ).lower()
                        == "y"
                    )
                else:
                    has_pack = False

                results = manager.search_beats(query, search_by, has_pack)

                if results:
                    print("Search results:")
                    for item in results:
                        print(item)

                else:
                    print(f"No {item_type.lower()}s found matching that criteria.")

            case _:
                print("Invalid command. Please try again.")


if __name__ == "__main__":
    main()
