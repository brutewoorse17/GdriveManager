import os
import threading
import logging
import time

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

@app.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    # Get credentials file when the bot starts
    global credentials_file
    credentials_file = await get_credentials_file(client, message)
    if not credentials_file:
        await message.reply_text("Failed to obtain credentials.json. Exiting...")
        exit(1)

    # ... rest of your start_command logic ...

# ... (rest of the code) ...