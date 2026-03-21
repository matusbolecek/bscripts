import os
import re

def rename_loops(folder_path):
    pattern = r'@(\w+)\s*~\s*(.+?)\s+(\d+)\s+([A-G]#?b?m?)'
    
    if not os.path.isdir(folder_path):
        print(f"Error: The folder '{folder_path}' does not exist.")
        return

    files_renamed = 0
    files_processed = 0

    print(f"Scanning folder: {folder_path}")

    for filename in os.listdir(folder_path):
        files_processed += 1
        
        if filename.endswith('.mp3'):
            match = re.search(pattern, filename)
            if match:
                username, name, bpm, key = match.groups()
                name = name.strip()
                
                new_filename = f"{name} {bpm} {key} @{username}.mp3"
                
                old_path = os.path.join(folder_path, filename)
                new_path = os.path.join(folder_path, new_filename)
                os.rename(old_path, new_path)
                print(f"Renamed: {filename} -> {new_filename}")
                files_renamed += 1

    print(f"\nProcess completed.")
    print(f"Total files processed: {files_processed}")
    print(f"Files renamed: {files_renamed}")
    print(f"Files skipped: {files_processed - files_renamed}")

folder_path = input("Please enter the path to the folder containing your audio loops: ").strip().strip("'\"")
rename_loops(folder_path)