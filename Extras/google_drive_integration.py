import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/drive.file']

def get_google_drive_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    return build('drive', 'v3', credentials=creds)

def create_folder(service, folder_name, parent_id=None):
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if parent_id:
        file_metadata['parents'] = [parent_id]
    
    folder = service.files().create(body=file_metadata, fields='id').execute()
    return folder.get('id')

def upload_file(service, file_path, folder_id):
    file_name = os.path.basename(file_path)
    file_metadata = {
        'name': file_name,
        'parents': [folder_id]
    }
    media = MediaFileUpload(file_path, resumable=True)
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    
    # Set the file to be publicly accessible
    permission = {
        'type': 'anyone',
        'role': 'reader',
        'allowFileDiscovery': False
    }
    service.permissions().create(fileId=file['id'], body=permission).execute()
    
    # Generate direct download link with file extension
    file_extension = os.path.splitext(file_name)[1]
    direct_link = f"https://drive.google.com/uc?export=download&id={file['id']}&confirm=t&filename={file_name}"
    return direct_link

def process_files_with_drive(folder_path, drive_folder_name):
    service = get_google_drive_service()
    drive_folder_id = create_folder(service, drive_folder_name)
    
    for filename in os.listdir(folder_path):
        if filename.endswith(('.mp4', '.mov')):
            file_path = os.path.join(folder_path, filename)
            direct_link = upload_file(service, file_path, drive_folder_id)
            yield filename, direct_link

if __name__ == "__main__":
    pass