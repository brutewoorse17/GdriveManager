import os
import threading
import logging
import time
import asyncio

from pyrogram import Client, filters
from pyrogram.types import Message
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os.path
import pickle
import flask  # For the web server

# Configure logging
logging.basicConfig(level=logging.ERROR,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Pyrogram bot setup
API_ID = '29001415'  # Replace with your API ID
API_HASH = '92152fd62ffbff12f057edc057f978f1'  # Replace with your API hash
BOT_TOKEN = '7505846620:AAFvv-sFybGfFILS-dRC8l7ph_0rqIhDgRM'  # Replace with your bot token

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Function to auto-detect and upload credentials.json
async def get_credentials_file(client, message):
    """
    Auto-detects the credentials.json file and uploads it to the bot directory.
    """
    try:
        # Check if credentials.json exists in the current directory
        if os.path.exists("credentials.json"):
            return "credentials.json"

        # If not found, prompt the user to upload the file
        await message.reply_text("credentials.json not found. Please upload the file:")

        credentials_file = None  # Initialize credentials_file

        @app.on_message(filters.document)
        async def handle_credentials_upload(client, message):
            global credentials_file
            # Check if the uploaded file is named "credentials.json"
            if message.document.file_name == "credentials.json":
                # Download the file to the bot directory
                credentials_file = await message.download()
                print(f"credentials.json uploaded successfully: {credentials_file}")
                # Remove the handler to stop listening for more documents
                app.remove_handler(handle_credentials_upload)

        # Wait for the user to upload the file with a timeout
        timeout = 60  # Timeout in seconds
        start_time = time.time()
        while credentials_file is None and time.time() - start_time < timeout:
            await asyncio.sleep(1)  # Use asyncio.sleep for async waiting

        if credentials_file is None:
            await message.reply_text("Timeout waiting for credentials.json upload.")
            return None

        return credentials_file

    except Exception as e:
        logger.exception("Error getting credentials file")
        await message.reply_text(f"Error getting credentials file: {e}")
        return None

# Global variable to store the credentials file path
credentials_file = None

@app.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    # Get credentials file when the bot starts
    global credentials_file, service  # Declare service as global
    credentials_file = await get_credentials_file(client, message)
    if not credentials_file:
        await message.reply_text("Failed to obtain credentials.json. Exiting...")
        exit(1)

    # Google Drive API setup (moved inside start_command)
    SCOPES = ['https://www.googleapis.com/auth/drive']
    creds = None
    try:
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        service = build('drive', 'v3', credentials=creds)  # Assign to the global service variable
        await message.reply_text("Google Drive API setup successful!")
    except Exception as e:
        logger.exception("Error setting up Google Drive API")
        await message.reply_text(f"Failed to set up Google Drive API: {e}")

# Flask app for handling the redirect
flask_app = flask.Flask(__name__)

# Global variable to store the authorization code
auth_code = None

@flask_app.route("/oauth2callback")
def oauth2callback():
    global auth_code
    auth_code = flask.request.args.get("code")
    print(f"Received auth code: {auth_code}")
    return "Authorization successful! You can close this window."

@app.on_message(filters.command("auth_google"))
async def auth_google_command(client: Client, message: Message):
    global auth_code
    try:
        # 1. Generate authorization URL
        flow = InstalledAppFlow.from_client_secrets_file(
            credentials_file, SCOPES)  # Use credentials_file here
        flow.redirect_uri = "http://localhost:5000/oauth2callback"
        auth_url, _ = flow.authorization_url(prompt="consent")

        # 2. Send authorization URL to the user
        await message.reply_text(f"Please visit this URL to authorize: {auth_url}")

        # 3. Start a web server to listen for the authorization code
        threading.Thread(target=flask_app.run, kwargs={'port': 5000}).start()

        # 4. Wait for the authorization code with a timeout
        timeout = 60  # Timeout in seconds
        start_time = time.time()
        while auth_code is None and time.time() - start_time < timeout:
            await asyncio.sleep(1)

        if auth_code is None:
            await message.reply_text("Timeout waiting for authorization.")
            return

        # 5. Exchange code for tokens
        flow.fetch_token(code=auth_code)

        # 6. Access credentials
        credentials = flow.credentials
        # ... use credentials to access Google APIs ...

        await message.reply_text("Authorization successful!")

    except Exception as e:
        logger.exception("Error during authorization")
        await message.reply_text(f"Authorization failed: {e}")

@app.on_message(filters.command("create_folder"))
async def create_folder_command(client: Client, message: Message):
    try:
        folder_name = ' '.join(message.command[1:])
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        file = service.files().create(body=file_metadata, fields='id').execute()  # Access the global service
        await message.reply_text(f"Folder '{folder_name}' created with ID: {file.get('id')}")
    except Exception as e:
        logger.exception("Error creating folder")
        await message.reply_text(f"Failed to create folder: {e}")

@app.on_message(filters.command("create_multiple_folders"))
async def create_multiple_folders_command(client: Client, message: Message):
    try:
        folder_names = ' '.join(message.command[1:]).split(',')
        for folder_name in folder_names:
            file_metadata = {
                'name': folder_name.strip(),
                'mimeType': 'application/vnd.google-apps.folder'
            }
            file = service.files().create(body=file_metadata, fields='id').execute()  # Access the global service
            await message.reply_text(f"Folder '{folder_name.strip()}' created with ID: {file.get('id')}")
    except Exception as e:
        logger.exception("Error creating multiple folders")
        await message.reply_text(f"Failed to create folders: {e}")

@app.on_message(filters.text)
async def echo(client: Client, message: Message):
    await message.reply_text(message.text)

app.run()