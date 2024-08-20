import os
import shutil
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from beat_management import BeatManager, Beat
from beatstars_config import Management

SCOPES = ['https://www.googleapis.com/auth/drive']

def get_google_drive_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('Extras/token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('Extras/credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    return build('drive', 'v3', credentials=creds)

def get_or_create_folder(service, folder_name, parent_folder_id=None):
    query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
    if parent_folder_id:
        query += f" and '{parent_folder_id}' in parents"
    
    print(f"Searching for active folder: '{folder_name}'")
    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    items = results.get('files', [])
    
    print(f"Found {len(items)} active folders matching '{folder_name}':")
    for item in items:
        print(f"  - {item['name']} (ID: {item['id']})")
    
    if items:
        print(f"Using existing active folder: {items[0]['name']} (ID: {items[0]['id']})")
        return items[0]['id']
    else:
        print(f"No active folder found. Creating new folder: {folder_name}")
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_folder_id:
            file_metadata['parents'] = [parent_folder_id]
        try:
            folder = service.files().create(body=file_metadata, fields='id').execute()
            print(f"Created new folder with ID: {folder.get('id')}")
            return folder.get('id')
        except Exception as e:
            print(f"Error creating folder: {str(e)}")
            return None

def upload_files(service, local_folder_path, drive_folder_id):
    print(f"Uploading files from: {local_folder_path}")
    all_files_uploaded = True
    for item in os.listdir(local_folder_path):
        item_path = os.path.join(local_folder_path, item)
        if os.path.isfile(item_path):
            print(f"Uploading file: {item}")
            file_metadata = {
                'name': item,
                'parents': [drive_folder_id]
            }
            media = MediaFileUpload(item_path, resumable=True)
            try:
                file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
                print(f"Uploaded file with ID: {file.get('id')}")
            except Exception as e:
                print(f"Error uploading file {item}: {str(e)}")
                all_files_uploaded = False
    return all_files_uploaded

def get_beat_info_from_folder_name(folder_name, beat_manager):
    print(f"Parsing folder name: {folder_name}")
    beat = beat_manager.parse_filename(folder_name)
    print(f"Parsed beat: {beat.name}, {beat.tempo}, {beat.key}")
    
    existing_beats = beat_manager.search_beats(beat.name, search_by='name')
    
    if not existing_beats:
        beat_manager.add_beat(beat)
        print(f"Added new beat to database: {beat.name}")
    else:
        beat = Beat(*existing_beats[0][1:])
        print(f"Found existing beat in database: {beat.name}, {beat.tempo}, {beat.key}")
    
    return beat.name, str(beat.tempo), beat.key

def process_and_upload_folder(local_folder_path, drive_folder_name, delete_after_upload=True):
    service = get_google_drive_service()
    beat_manager = BeatManager(Management.database_path_beats)

    try:
        print(f"Processing folder: {local_folder_path}")
        drive_folder_id = get_or_create_folder(service, drive_folder_name)
        
        if os.path.isdir(local_folder_path):
            folder_name = os.path.basename(local_folder_path)
            beat_name, bpm, key = get_beat_info_from_folder_name(folder_name, beat_manager)
            new_folder_name = f"{beat_name}, {bpm}, {key}"
            
            print(f"Attempting to create folder: {new_folder_name}")
            new_folder_id = get_or_create_folder(service, new_folder_name, drive_folder_id)
            if new_folder_id:
                print(f"Created folder with ID: {new_folder_id}")
                print(f"Uploading files from: {local_folder_path}")
                upload_successful = upload_files(service, local_folder_path, new_folder_id)
                if upload_successful:
                    print("Upload complete")
                    print(f"Uploaded: {folder_name} -> {new_folder_name}")
                    
                    if delete_after_upload:
                        try:
                            shutil.rmtree(local_folder_path)
                            print(f"Deleted local folder: {folder_name}")
                        except Exception as e:
                            print(f"Error deleting local folder {folder_name}: {str(e)}")
                else:
                    print("Upload incomplete. Local folder not deleted.")
            else:
                print(f"Failed to create or find folder: {new_folder_name}")
        else:
            print(f"Error: {local_folder_path} is not a valid directory.")
    except Exception as e:
        print(f"Error processing folder '{local_folder_path}': {str(e)}")
    finally:
        beat_manager.close()

def process_multiple_folders(base_folder_path, drive_folder_name, delete_after_upload=True):
    for folder_name in os.listdir(base_folder_path):
        folder_path = os.path.join(base_folder_path, folder_name)
        if os.path.isdir(folder_path):
            process_and_upload_folder(folder_path, drive_folder_name, delete_after_upload)

if __name__ == "__main__":
    base_folder_path = input('Insert the local folder path: ').strip().strip("'\"")
    drive_folder_name = input('Insert the Google Drive folder name: ').strip()
    delete_option = input('Delete local folders after successful upload? (y/n): ').strip().lower()
    delete_after_upload = delete_option == 'y'
    
    print(f"Processing folder: {base_folder_path}")
    print(f"Uploading to Google Drive folder: {drive_folder_name}")
    print(f"Delete after upload: {'Yes' if delete_after_upload else 'No'}")
    
    if not os.path.exists(base_folder_path):
        print(f"Error: The path '{base_folder_path}' does not exist.")
        exit(1)
    
    try:
        process_multiple_folders(base_folder_path, drive_folder_name, delete_after_upload)
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")