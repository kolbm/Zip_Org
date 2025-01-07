import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from io import BytesIO
import zipfile
import os
import requests

# Google Drive API Scope
SCOPES = ['https://www.googleapis.com/auth/drive']

# Authenticate with Google API
def authenticate():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds

# Download file from Google Drive
def download_file(drive_service, file_id, mime_type=None):
    if mime_type:
        request = drive_service.files().export_media(fileId=file_id, mimeType=mime_type)
    else:
        request = drive_service.files().get_media(fileId=file_id)
    fh = BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    fh.seek(0)
    return fh

# Function to organize files and create ZIPs
def organize_and_zip_submissions(folder_id):
    creds = authenticate()
    drive_service = build('drive', 'v3', credentials=creds)

    # List files in folder
    results = drive_service.files().list(q=f"'{folder_id}' in parents", pageSize=1000, fields="files(id, name, mimeType, owners)").execute()
    files = results.get('files', [])

    if not files:
        st.error("No files found in the folder.")
        return

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zipf:
        progress = st.progress(0)
        for i, file in enumerate(files):
            owner_name = file['owners'][0]['displayName'].replace(" ", "_")
            file_name = file['name']
            file_extension = ".docx" if file['mimeType'] == 'application/vnd.google-apps.document' else os.path.splitext(file_name)[-1]

            # Download file (convert Google Docs to Word if necessary)
            if file['mimeType'] == 'application/vnd.google-apps.document':
                file_blob = download_file(drive_service, file['id'], mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                zip_name = f"{owner_name}/{file_name.replace('.gdoc', '')}{file_extension}"
            else:
                file_blob = download_file(drive_service, file['id'])
                zip_name = f"{owner_name}/{file_name}"

            zipf.writestr(zip_name, file_blob.read())
            progress.progress((i + 1) / len(files))

    st.success("ZIP creation completed!")
    st.download_button("Download ZIP", data=zip_buffer.getvalue(), file_name="submissions.zip", mime="application/zip")

# Streamlit App UI
def main():
    st.title("Organize and Zip Submissions")
    folder_id = st.text_input("Enter Google Drive Folder ID:", help="Paste your Google Drive folder ID here.")
    if st.button("Organize and ZIP"):
        if folder_id:
            organize_and_zip_submissions(folder_id)
        else:
            st.error("Please enter a valid folder ID.")

if __name__ == "__main__":
    main()
