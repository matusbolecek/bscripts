import os
import shutil

def organize_files(folder_path):
    if not os.path.exists(folder_path):
        print(f"The folder {folder_path} does not exist.")
        return

    # Iterate through all files in the folder
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        
        if os.path.isfile(file_path):
            file_name_without_ext = os.path.splitext(filename)[0]
            
            new_folder_path = os.path.join(folder_path, file_name_without_ext)
            os.makedirs(new_folder_path, exist_ok=True)
            
            new_file_path = os.path.join(new_folder_path, filename)
            shutil.move(file_path, new_file_path)
            
            print(f"Moved {filename} to {new_file_path}")

if __name__ == "__main__":
    folder_path = input("Enter the folder path: ")
    folder_path = folder_path.strip("'\"")
    organize_files(folder_path)