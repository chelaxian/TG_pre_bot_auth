#!/usr/bin/env python3
"""
This file, authenticator.py, is the entry point for the bot.
It performs phone number verification (using the allowed numbers file and temporary numbers file)
before an update is passed to the main bot logic.
Until the user is authorized, the bot responds to every message
with a request to share a contact. If the phone number (after normalization)
in the sent contact is found in the allowed numbers file or in the temporary numbers file,
the user is considered authorized and their update is passed to the main script.
"""
import os
import runpy
import logging
import json
from dotenv import load_dotenv
from telegram.ext import Application
# Load environment variables
load_dotenv()

#############################
# CONFIGURATION
#############################
# Bot token – preferably taken from environment; if not set, you can explicitly specify it here.
# If the token remains as "YOUR_BOT_TOKEN_HERE", the authenticator will log a warning and skip launching the bot.
BOT_TOKEN = os.environ.get('BOT_TOKEN') or "YOUR_BOT_TOKEN_HERE"

# Path to the file that stores allowed phone numbers (one per line).
ALLOWED_NUMBERS_FILE = os.environ.get('ALLOWED_NUMBERS_FILE', "/root/Telegram/BACKUP/phone_numbers.txt")

# Path to the JSON file that stores temporary phone numbers.
TEMP_PHONE_FILE = os.environ.get('TEMP_PHONE_FILE', "/root/Telegram/BACKUP/temp_phone_numbers.json")

# Main script to run (e.g., bot.py). You can change this to run a different module.
MAIN_SCRIPT = os.environ.get('MAIN_SCRIPT', "bot")

#############################
# END CONFIGURATION
#############################

# Set up logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Update configuration in config.py if necessary
import config
config.BOT_TOKEN = BOT_TOKEN

# Read the allowed phone numbers from ALLOWED_NUMBERS_FILE.
allowed_numbers = set()
if os.path.exists(ALLOWED_NUMBERS_FILE):
    with open(ALLOWED_NUMBERS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            number = line.strip()
            if number:
                allowed_numbers.add(number)
    logger.info("Allowed numbers loaded: %s", allowed_numbers)
else:
    logger.warning("File %s not found – the allowed numbers list will be empty.", ALLOWED_NUMBERS_FILE)

# Global dictionary to store authorized users: key – user ID, value – True/False.
authorized_users = {}

# Save the original process_update method.
original_process_update = Application.process_update

def normalize_number(phone: str) -> str:
    """
    Remove spaces, dashes, and parentheses and ensure the number starts with a plus.
    """
    import re
    phone = re.sub(r"[\s\-()]", "", phone)
    if not phone.startswith("+"):
        phone = "+" + phone
    return phone

def read_temp_numbers():
    """
    Read temporary phone numbers from TEMP_PHONE_FILE.
    Returns a list of dicts with at least a "phone" key.
    """
    if os.path.exists(TEMP_PHONE_FILE):
        try:
            with open(TEMP_PHONE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception as e:
            logger.error("Error reading temporary numbers: %s", e)
    return []

async def new_process_update(self, update):
    """
    Global update interceptor for authorization.
    If the user is not yet authorized, the update is not passed to the handlers in the main script.
    If the update contains a contact, the phone number is checked – and if it matches (in allowed or temporary lists),
    the user is authorized.
    """
    user = update.effective_user
    message = update.effective_message
    if user is None:
        await original_process_update(self, update)
        return

    user_id = user.id

    # If the user is already authorized, pass the update on.
    if authorized_users.get(user_id, False):
        await original_process_update(self, update)
        return

    # If the update contains a contact, try to authorize the user.
    if message and message.contact:
        contact = message.contact
        logger.info("Received contact from user_id=%s: phone=%s, contact.user_id=%s",
                    user_id, contact.phone_number, contact.user_id)
        if (contact.user_id == user_id) or (contact.user_id is None):
            phone = contact.phone_number.replace(" ", "").replace("-", "")
            if not phone.startswith("+"):
                phone = "+" + phone
            logger.info("Normalized number: %s", phone)
            try:
                temp_data = read_temp_numbers()
                temp_numbers = {entry.get("phone") for entry in temp_data if isinstance(entry, dict)}
            except Exception:
                temp_numbers = set()
            if phone in allowed_numbers or phone in temp_numbers:
                authorized_users[user_id] = True
                await message.reply_text("Authorization successful. You can now use the bot.")
                from telegram import ReplyKeyboardRemove
                await message.reply_text("Continuing work.", reply_markup=ReplyKeyboardRemove())
                await original_process_update(self, update)
                return
            else:
                await message.reply_text("Access denied. Your number was not found in the allowed list.")
                return
        else:
            await message.reply_text("Please send your own contact.")
            return

    # If the update does not contain a contact, prompt user to share contact.
    from telegram import KeyboardButton, ReplyKeyboardMarkup
    button = KeyboardButton("Share Contact", request_contact=True)
    reply_markup = ReplyKeyboardMarkup([[button]], one_time_keyboard=True, resize_keyboard=True)
    if message:
        await message.reply_text(
            "To use the bot, you must be authorized.\n"
            "Please click the button below to share your contact.",
            reply_markup=reply_markup
        )
    return

# Monkey-patch: replace Application.process_update with our version.
Application.process_update = new_process_update

# For compatibility, override decorators if used in the main script.
import utils.decorators as decorators
def dummy_auth(func):
    return func
decorators.Authorization = dummy_auth
decorators.GroupAuthorization = dummy_auth

logger.info("Launching main module %s...", MAIN_SCRIPT)

# Only launch the main module if BOT_TOKEN is not the placeholder.
if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
    logger.warning("BOT_TOKEN is not set to a real token. Skipping bot launch.")
else:
    runpy.run_module(MAIN_SCRIPT, run_name="__main__")
