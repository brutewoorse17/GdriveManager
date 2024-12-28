import os
import threading
import logging

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

# Function to install requirements
def install_requirements(requirements_file="requirements.txt"):
    """
    Installs the required packages from a requirements.txt file.
    """
    try:
        os.system(f"pip install -r {requirements_file}")
        print("Requirements installed successfully!")
    except Exception as e:
        logger.exception("Error installing requirements")  # Log the exception

# Install requirements
install_requirements()

# Google Drive API setup
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
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    service = build('drive', 'v3', credentials=creds)
except Exception as e:
    logger.exception("Error setting up Google Drive API")

# Pyrogram bot setup
API_ID = 'YOUR_API_ID'  # Replace with your API ID
API_HASH = 'YOUR_API_HASH'  # Replace with your API hash
BOT_TOKEN = 'YOUR_BOT_TOKEN'  # Replace with your bot token

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Flask app for handling the redirect
flask_app = flask.Flask(__name__)

# Global variable to store the authorization code
auth_code = None

@flask_app.route("/oauth2callback")
def oauth2callback():
    global auth_code
    auth_code = flask.request.args.get("code")
    # This is a basic example; in a real app, you'd want to
    # do more than just print the code to the console.
    print(f"Received auth code: {auth_code}")
    return "Authorization successful! You can close this window."

@app.on_message(filters.command("auth_google"))
async def auth_google_command(client: Client, message: Message):
    global auth_code
    try:
        # 1. Generate authorization URL
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES)
        flow.redirect_uri = "http://localhost:5000/oauth2callback"  # Your redirect URI
        auth_url, _ = flow.authorization_url(prompt="consent")

        # 2. Send authorization URL to the user
        await message.reply_text(f"Please visit this URL to authorize: {auth_url}")

        # 3. Start a web server to listen for the authorization code in a separate thread
        threading.Thread(target=flask_app.run, kwargs={'port': 5000}).start()

        # 4. Wait for the authorization code
        while auth_code is None:
            pass  # This is a simple wait; consider using a more robust mechanism

        # 5. Exchange code for tokens
        flow.fetch_token(code=auth_code)

        # 6. Access credentials
        credentials = flow.credentials
        # ... use credentials to access Google APIs ...

        await message.reply_text("Authorization successful!")

    except Exception as e:
        logger.exception("Error during authorization")  # Log the exception
        await message.reply_text(f"Authorization failed: {e}")

@app.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    await message.reply_text("I'm a bot, please talk to me!")

@app.on_message(filters.command("create_folder"))
async def create_folder_command(client: Client, message: Message):
    try:
        folder_name = ' '.join(message.command[1:])
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        file = service.files().create(body=file_metadata, fields='id').execute()
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
            file = service.files().create(body=file_metadata, fields='id').execute()
            await message.reply_text(f"Folder '{folder_name.strip()}' created with ID: {file.get('id')}")
    except Exception as e:
        logger.exception("Error creating multiple folders")
        await message.reply_text(f"Failed to create folders: {e}")

@app.on_message(filters.text)
async def echo(client: Client, message: Message):
    await message.reply_text(message.text)

app.run()
logger.info("Bot is Booted")