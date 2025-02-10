#!/usr/bin/env python3
"""
This file, authenticator.py, is the entry point for the bot.
It performs phone number verification (using the phone_numbers.txt file)
before an update is passed to the main logic in bot.py.
Until the user is authorized, the bot responds to every message
with a request to share a contact. If the phone number (after normalization)
in the sent contact is found in phone_numbers.txt, the user is considered
authorized and their update is passed to bot.py.
"""

import os
import runpy
import logging
from dotenv import load_dotenv
from telegram.ext import Application

# Load environment variables
load_dotenv()

# Set up logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Read the bot token – now it is defined only in this file.
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("Environment variable BOT_TOKEN is not set!")

# If necessary, update the configuration (for example, in config.py)
import config
config.BOT_TOKEN = BOT_TOKEN

# Read the list of allowed phone numbers from phone_numbers.txt
# Expected format: one phone number (e.g., +79262355196) per line.
allowed_numbers = set()
phone_numbers_file = "phone_numbers.txt"
if os.path.exists(phone_numbers_file):
    with open(phone_numbers_file, "r", encoding="utf-8") as f:
        for line in f:
            number = line.strip()
            if number:
                allowed_numbers.add(number)
    logger.info("Allowed numbers loaded: %s", allowed_numbers)
else:
    logger.warning("File %s not found – the allowed numbers list will be empty.", phone_numbers_file)

# Global dictionary to store authorized users:
# key – user ID, value – True/False.
authorized_users = {}

# Save the original process_update method
original_process_update = Application.process_update

async def new_process_update(self, update):
    """
    Global update interceptor for authorization.
    If the user is not yet authorized, the update is not passed to the handlers in bot.py.
    If the update contains a contact, the phone number is checked – and if it matches,
    the user is authorized.
    """
    user = update.effective_user
    message = update.effective_message
    if user is None:
        # If there's no user info, pass the update on.
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
        # Check that the contact belongs to the sender (or contact.user_id is missing)
        if (contact.user_id == user_id) or (contact.user_id is None):
            # Normalize the phone number: remove spaces and dashes, and ensure it starts with "+"
            phone = contact.phone_number.replace(" ", "").replace("-", "")
            if not phone.startswith("+"):
                phone = "+" + phone
            logger.info("Normalized number: %s", phone)
            if phone in allowed_numbers:
                authorized_users[user_id] = True
                await message.reply_text("Authorization successful. You can now use the bot.")
                # Remove the keyboard with the contact request
                from telegram import ReplyKeyboardRemove
                await message.reply_text("Continuing work.", reply_markup=ReplyKeyboardRemove())
                # Pass the update to the main logic
                await original_process_update(self, update)
                return
            else:
                await message.reply_text("Access denied. Your number was not found in the allowed list.")
                return
        else:
            await message.reply_text("Please send your own contact.")
            return

    # If the update does not contain a contact, send a request with a "Share Contact" button.
    from telegram import KeyboardButton, ReplyKeyboardMarkup
    button = KeyboardButton("Share Contact", request_contact=True)
    reply_markup = ReplyKeyboardMarkup([[button]], one_time_keyboard=True, resize_keyboard=True)
    if message:
        await message.reply_text(
            "To use the bot, you must be authorized.\n"
            "Please click the button below to share your contact.",
            reply_markup=reply_markup
        )
    # Do not pass the update further until the user is authorized.
    return

# Monkey-patch: replace Application.process_update with our version.
Application.process_update = new_process_update

# (For compatibility we can leave our previous monkey-patching of decorators,
# but it is not necessary since the global interceptor handles all updates.)
import utils.decorators as decorators
def dummy_auth(func):
    return func
decorators.Authorization = dummy_auth
decorators.GroupAuthorization = dummy_auth

logger.info("Launching main module bot.py...")

# Run the main module bot.py. Now all updates pass through our new_process_update.
if __name__ == "__main__":
    runpy.run_module("bot", run_name="__main__")
