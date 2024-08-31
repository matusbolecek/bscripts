import os
import dropbox
from dropbox.exceptions import AuthError
from dropbox.files import WriteMode
import re

from beatstars_config import Publisher

def get_dropbox_service(access_token):
    try:
        dbx = dropbox.Dropbox(access_token)
        dbx.users_get_current_account()
        return dbx
    except AuthError:
        print("ERROR: Invalid access token.")
        return None

def sanitize_path(path):
    # Remove invalid characters and replace spaces with underscores
    sanitized = re.sub(r'[<>:"/\\|?*\s]', '_', path)
    # Ensure the path is UTF-8 encoded
    return sanitized.encode('utf-8', errors='ignore').decode('utf-8')

def create_folder(dbx, folder_name, parent_path=''):
    folder_name = sanitize_path(folder_name)
    full_path = f"/{folder_name}" if not parent_path else f"{parent_path}/{folder_name}"
    try:
        dbx.files_create_folder_v2(full_path)
        return full_path
    except dropbox.exceptions.ApiError as e:
        if isinstance(e.error, dropbox.files.CreateFolderError) and e.error.is_path() and e.error.get_path().is_conflict():
            print(f"Folder already exists: {full_path}")
            return full_path
        else:
            print(f"Error creating folder: {e}")
            return None

def upload_file(dbx, file_path, folder_path):
    file_name = sanitize_path(os.path.basename(file_path))
    dropbox_path = f"{folder_path}/{file_name}"

    with open(file_path, 'rb') as f:
        try:
            dbx.files_upload(f.read(), dropbox_path, mode=WriteMode('overwrite'))
            shared_link = dbx.sharing_create_shared_link_with_settings(dropbox_path)
            # Convert the shared link to a direct download link
            direct_link = shared_link.url.replace('www.dropbox.com', 'dl.dropboxusercontent.com')
            direct_link = direct_link.replace('?dl=0', '')
            return direct_link
        except dropbox.exceptions.ApiError as e:
            print(f"Error uploading file: {e}")
            return None

def process_files_with_dropbox(folder_path, dropbox_folder_name, token):
    dbx = get_dropbox_service(token)
    if not dbx:
        print("Failed to initialize Dropbox service")
        return

    dropbox_folder_path = create_folder(dbx, dropbox_folder_name)
    if not dropbox_folder_path:
        print(f"Failed to create or access folder: {dropbox_folder_name}")
        return

    for filename in os.listdir(folder_path):
        try:
            if filename.endswith(('.mp4', '.mov', '.jpg', '.jpeg', '.png', '.gif', '.srt')):
                file_path = os.path.join(folder_path, filename)
                print(f"Processing file: {file_path}")
                direct_link = upload_file(dbx, file_path, dropbox_folder_path)
                if direct_link:
                    yield filename, direct_link
                else:
                    print(f"Failed to upload file: {filename}")
        except Exception as e:
            print(f"Error processing file {filename}: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    pass