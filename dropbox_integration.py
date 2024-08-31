import os
import dropbox
from dropbox.exceptions import AuthError
from dropbox.files import WriteMode
import re
import logging
from beatstars_config import Publisher

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def get_dropbox_service(access_token):
    logging.info("Attempting to initialize Dropbox service")
    try:
        dbx = dropbox.Dropbox(access_token)
        dbx.users_get_current_account()
        logging.info("Dropbox service initialized successfully")
        return dbx
    except AuthError:
        logging.error("ERROR: Invalid access token.")
        return None

def sanitize_path(path):
    logging.debug(f"Sanitizing path: {path}")
    # Remove invalid characters but keep the file extension
    base, ext = os.path.splitext(path)
    sanitized_base = re.sub(r'[<>:"/\\|?*]', '_', base)
    sanitized = f"{sanitized_base}{ext}"
    sanitized = sanitized.encode('utf-8', errors='ignore').decode('utf-8')
    logging.debug(f"Sanitized path: {sanitized}")
    return sanitized

def create_folder(dbx, folder_name, parent_path=''):
    folder_name = sanitize_path(folder_name)
    full_path = f"/{folder_name}" if not parent_path else f"{parent_path}/{folder_name}"
    logging.info(f"Attempting to create folder: {full_path}")
    try:
        dbx.files_create_folder_v2(full_path)
        logging.info(f"Folder created successfully: {full_path}")
        return full_path
    except dropbox.exceptions.ApiError as e:
        if isinstance(e.error, dropbox.files.CreateFolderError) and e.error.is_path() and e.error.get_path().is_conflict():
            logging.info(f"Folder already exists: {full_path}")
            return full_path
        else:
            logging.error(f"Error creating folder: {e}")
            return None

def upload_file(dbx, file_path, folder_path):
    file_name = sanitize_path(os.path.basename(file_path))
    dropbox_path = f"{folder_path}/{file_name}"
    logging.info(f"Attempting to upload file: {file_path} to {dropbox_path}")
    with open(file_path, 'rb') as f:
        try:
            dbx.files_upload(f.read(), dropbox_path, mode=WriteMode('overwrite'))
            logging.info(f"File uploaded successfully: {dropbox_path}")
            shared_link = dbx.sharing_create_shared_link_with_settings(dropbox_path)
            direct_link = shared_link.url.replace('www.dropbox.com', 'dl.dropboxusercontent.com').replace('?dl=0', '')
            logging.info(f"Direct download link created: {direct_link}")
            return direct_link
        except dropbox.exceptions.ApiError as e:
            logging.error(f"Error uploading file: {e}")
            return None

def process_files_with_dropbox(folder_path, dropbox_folder_name, token):
    logging.info(f"Starting process_files_with_dropbox with folder_path: {folder_path}")
    dbx = get_dropbox_service(token)
    if not dbx:
        logging.error("Failed to initialize Dropbox service")
        return

    dropbox_folder_path = create_folder(dbx, dropbox_folder_name)
    if not dropbox_folder_path:
        logging.error(f"Failed to create or access folder: {dropbox_folder_name}")
        return

    logging.info(f"Contents of folder {folder_path}:")
    for filename in os.listdir(folder_path):
        logging.info(f"Found file: {filename}")
        try:
            if filename.endswith(('.mp4', '.mov', '.jpg', '.jpeg', '.png', '.gif', '.srt')):
                file_path = os.path.join(folder_path, filename)
                logging.info(f"Processing file: {file_path}")
                direct_link = upload_file(dbx, file_path, dropbox_folder_path)
                if direct_link:
                    logging.info(f"Successfully uploaded: {filename}")
                    yield filename, direct_link
                else:
                    logging.warning(f"Failed to upload file: {filename}")
            else:
                logging.info(f"Skipping file with unsupported extension: {filename}")
        except Exception as e:
            logging.error(f"Error processing file {filename}: {str(e)}")
            import traceback
            logging.error(traceback.format_exc())

if __name__ == "__main__":
    # You can add test code here if needed
    pass