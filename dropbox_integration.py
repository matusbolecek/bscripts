import os
import dropbox
from dropbox.exceptions import AuthError
from dropbox.files import WriteMode
import re
import logging
from beatstars_config import Publisher

# Set up logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Constants for chunked uploading
CHUNK_SIZE = 4 * 1024 * 1024  # 4MB chunks
VIDEO_EXTENSIONS = [".mp4", ".mov", ".avi", ".wmv"]


def get_dropbox_service(access_token):
    logging.info("Attempting to initialize Dropbox service")
    try:
        dbx = dropbox.Dropbox(
            access_token, timeout=300
        )  # Increased timeout to 5 minutes
        logging.info("Request to users/get_current_account")
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
    sanitized_base = re.sub(r'[<>:"/\\|?*]', "_", base)
    sanitized = f"{sanitized_base}{ext}"
    sanitized = sanitized.encode("utf-8", errors="ignore").decode("utf-8")
    logging.debug(f"Sanitized path: {sanitized}")
    return sanitized


def create_folder(dbx, folder_name, parent_path=""):
    folder_name = sanitize_path(folder_name)
    full_path = f"/{folder_name}" if not parent_path else f"{parent_path}/{folder_name}"
    logging.info(f"Attempting to create folder: {full_path}")
    try:
        logging.info("Request to files/create_folder_v2")
        dbx.files_create_folder_v2(full_path)
        logging.info(f"Folder created successfully: {full_path}")
        return full_path
    except dropbox.exceptions.ApiError as e:
        if (
            isinstance(e.error, dropbox.files.CreateFolderError)
            and e.error.is_path()
            and e.error.get_path().is_conflict()
        ):
            logging.info(f"Folder already exists: {full_path}")
            return full_path
        else:
            logging.error(f"Error creating folder: {e}")
            return None


def upload_file_standard(dbx, file_path, dropbox_path):
    with open(file_path, "rb") as f:
        try:
            logging.info("Request to files/upload")
            dbx.files_upload(f.read(), dropbox_path, mode=WriteMode("overwrite"))
            logging.info(f"File uploaded successfully: {dropbox_path}")
            return True
        except Exception as e:
            logging.error(f"Error uploading file: {e}")
            return False


def upload_file_chunked(dbx, file_path, dropbox_path):
    file_size = os.path.getsize(file_path)

    logging.info(f"Starting chunked upload for {file_path} ({file_size} bytes)")

    try:
        with open(file_path, "rb") as f:
            upload_session_start_result = dbx.files_upload_session_start(
                f.read(CHUNK_SIZE)
            )
            cursor = dropbox.files.UploadSessionCursor(
                session_id=upload_session_start_result.session_id, offset=f.tell()
            )
            commit = dropbox.files.CommitInfo(
                path=dropbox_path, mode=WriteMode("overwrite")
            )

            chunks_uploaded = 1
            logging.info(f"Uploaded chunk 1 ({CHUNK_SIZE} bytes)")

            while f.tell() < file_size:
                if (file_size - f.tell()) <= CHUNK_SIZE:
                    # Final chunk
                    dbx.files_upload_session_finish(f.read(CHUNK_SIZE), cursor, commit)
                    chunks_uploaded += 1
                    logging.info(
                        f"Uploaded final chunk {chunks_uploaded} ({min(CHUNK_SIZE, file_size - f.tell() + CHUNK_SIZE)} bytes)"
                    )
                else:
                    # Intermediate chunk
                    dbx.files_upload_session_append_v2(f.read(CHUNK_SIZE), cursor)
                    cursor.offset = f.tell()
                    chunks_uploaded += 1
                    logging.info(
                        f"Uploaded chunk {chunks_uploaded} ({CHUNK_SIZE} bytes)"
                    )

                    # Add a progress indicator every 10 chunks
                    if chunks_uploaded % 10 == 0:
                        progress = (f.tell() / file_size) * 100
                        logging.info(
                            f"Upload progress: {progress:.1f}% ({f.tell()} / {file_size} bytes)"
                        )

            logging.info(f"File uploaded successfully: {dropbox_path}")
            return True

    except Exception as e:
        logging.error(f"Error during chunked upload: {e}")
        import traceback

        logging.error(traceback.format_exc())
        return False


def upload_file(dbx, file_path, folder_path):
    file_name = sanitize_path(os.path.basename(file_path))
    dropbox_path = f"{folder_path}/{file_name}"
    logging.info(f"Attempting to upload file: {file_path} to {dropbox_path}")

    file_extension = os.path.splitext(file_path)[1].lower()
    file_size = os.path.getsize(file_path)

    # Use chunked upload for video files or any file larger than 10MB
    use_chunked = file_extension in VIDEO_EXTENSIONS or file_size > 10 * 1024 * 1024

    # Attempt upload
    upload_successful = False
    if use_chunked:
        logging.info(f"Using chunked upload for {file_path} ({file_size} bytes)")
        upload_successful = upload_file_chunked(dbx, file_path, dropbox_path)
    else:
        logging.info(f"Using standard upload for {file_path} ({file_size} bytes)")
        upload_successful = upload_file_standard(dbx, file_path, dropbox_path)

    # Create shared link if upload was successful
    if upload_successful:
        try:
            logging.info("Request to sharing/create_shared_link_with_settings")
            shared_link = dbx.sharing_create_shared_link_with_settings(dropbox_path)
            direct_link = shared_link.url.replace(
                "www.dropbox.com", "dl.dropboxusercontent.com"
            ).replace("?dl=0", "?dl=1")
            logging.info(f"Direct download link created: {direct_link}")
            return direct_link
        except dropbox.exceptions.ApiError as e:
            logging.error(f"Error creating shared link: {e}")
            return None
    else:
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
            if filename.endswith(
                (".mp4", ".mov", ".jpg", ".jpeg", ".png", ".gif", ".srt")
            ):
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

