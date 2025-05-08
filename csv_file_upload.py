import os
import csv
import uuid
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv  

# Load values from .env file
load_dotenv()  # This loads variables from the .env file into the environment

# ==== CONFIG ====
SERVICE_JSON = os.getenv('SERVICE_JSON')
FOLDER_ID = os.getenv('FOLDER_ID')
USER_EMAIL = os.getenv('USER_EMAIL')
CSV_PATH = os.getenv('CSV_PATH')
OUTPUT_LOG = os.getenv('OUTPUT_LOG')
RESUME = os.getenv('RESUME') == 'True'  # Convert to boolean

# ==== DRIVE MANAGER ====
class DriveUploader:
    def __init__(self, json_path, folder_id, user=None):
        creds = Credentials.from_service_account_file(json_path, scopes=['https://www.googleapis.com/auth/drive.file'], subject=user)
        self.service = build('drive', 'v3', credentials=creds)
        self.folder = folder_id

    def upload(self, file_path):
        if not os.path.isfile(file_path):
            print(f"❌ Not found: {file_path}")
            return None, None
        ext = os.path.splitext(file_path)[1]
        uuid_name = f"{uuid.uuid4()}{ext}"
        media = MediaFileUpload(file_path, resumable=True)
        meta = {'name': uuid_name, 'parents': [self.folder]}
        try:
            f = self.service.files().create(body=meta, media_body=media, fields='id,name').execute()
            print(f"✅ {uuid_name} | ID: {f['id']}")
            return uuid_name, f['id']
        except Exception as e:
            print(f"❌ Upload failed: {e}")
            return uuid_name, None

# ==== UTILITIES ====
def read_csv(path):
    try:
        with open(path, 'r', newline='') as f:
            return [row['FilePath'] for row in csv.DictReader(f) if 'FilePath' in row]
    except:
        return []

def read_log(path):
    if not os.path.exists(path):
        return set()
    with open(path, 'r', newline='') as f:
        return {row['OriginalPath'] for row in csv.DictReader(f) if row.get('DriveFileID') not in ("", "Upload Failed")}

def write_log(path, data, write_header=False):
    exists = os.path.exists(path)
    with open(path, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['OriginalPath', 'UUIDFileName', 'DriveFileID'])
        if write_header and not exists:
            writer.writeheader()
        writer.writerow(data)

# ==== MAIN ====
if __name__ == '__main__':
    uploader = DriveUploader(SERVICE_JSON, FOLDER_ID, USER_EMAIL)
    files = read_csv(CSV_PATH)
    all_total = len(files)
    if RESUME:
        done = read_log(OUTPUT_LOG)
        files = [f for f in files if f not in done]
        print(f"🔁 Resuming: {len(files)} of {all_total} files")
    else:
        if os.path.exists(OUTPUT_LOG):
            os.remove(OUTPUT_LOG)
        print(f"🆕 Uploading: {all_total} files")
    for i, f in enumerate(files, 1):
        uuid_name, file_id = uploader.upload(f)
        write_log(OUTPUT_LOG, {'OriginalPath': f, 'UUIDFileName': uuid_name, 'DriveFileID': file_id or "Upload Failed"}, write_header=not os.path.exists(OUTPUT_LOG))
        print(f"📊 Progress: {i}/{len(files)} ({int(i / len(files) * 100)}%)\n")
