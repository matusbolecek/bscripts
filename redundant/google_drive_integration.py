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
    if os.path.exists('Extras/token.json'):
        creds = Credentials.from_authorized_user_file('Extras/token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('Extras/credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('Extras/token.json', 'w') as token:
            token.write(creds.to_json())
    
    return build('drive', 'v3', credentials=creds)

def get_or_create_folder(service, folder_name, parent_folder_id=None):
    query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
    if parent_folder_id:
        query += f" and '{parent_folder_id}' in parents"
    
    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    items = results.get('files', [])
    
    if items:
        return items[0]['id']
    else:
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_folder_id:
            file_metadata['parents'] = [parent_folder_id]
        folder = service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')

def upload_files(service, local_folder_path, drive_folder_id):
    all_files_uploaded = True
    for item in os.listdir(local_folder_path):
        item_path = os.path.join(local_folder_path, item)
        if os.path.isfile(item_path):
            file_metadata = {
                'name': item,
                'parents': [drive_folder_id]
            }
            media = MediaFileUpload(item_path, resumable=True)
            try:
                file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            except Exception as e:
                print(f"Error uploading file {item}: {str(e)}")
                all_files_uploaded = False
    return all_files_uploaded

def get_beat_info_from_folder_name(folder_name, beat_manager):
    beat = beat_manager.parse_filename(folder_name)
    
    existing_beats = beat_manager.search_beats(beat.name, search_by='name')
    
    if not existing_beats:
        beat_manager.add_beat(beat)
    else:
        beat = Beat(*existing_beats[0][1:])
    
    return beat.name, str(beat.tempo), beat.key

def process_and_upload_folder(local_folder_path, drive_folder_name, delete_after_upload=True):
    service = get_google_drive_service()
    beat_manager = BeatManager(Management.database_path_beats)

    try:
        drive_folder_id = get_or_create_folder(service, drive_folder_name)
        
        if os.path.isdir(local_folder_path):
            folder_name = os.path.basename(local_folder_path)
            beat_name, bpm, key = get_beat_info_from_folder_name(folder_name, beat_manager)
            new_folder_name = f"{beat_name}, {bpm}, {key}"
            
            new_folder_id = get_or_create_folder(service, new_folder_name, drive_folder_id)
            if new_folder_id:
                upload_successful = upload_files(service, local_folder_path, new_folder_id)
                if upload_successful:
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
    
    if not os.path.exists(base_folder_path):
        print(f"Error: The path '{base_folder_path}' does not exist.")
        exit(1)
    
    try:
        process_multiple_folders(base_folder_path, drive_folder_name, delete_after_upload)
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")