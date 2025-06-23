#!/usr/bin/env python3
"""
Version 1.0.0 - Pyrogram pre-auth bot: requires phone number authorization before launching magic.py
"""
import os
import json
import runpy
import logging
from pyrogram import Client, filters
from pyrogram.types import KeyboardButton, ReplyKeyboardMarkup
from dotenv import load_dotenv

load_dotenv()

# --- CONFIG ---
API_ID = int(os.environ.get('API_ID', '12345'))  # Укажи свой API_ID
API_HASH = os.environ.get('API_HASH', 'your_api_hash')  # Укажи свой API_HASH
BOT_TOKEN = os.environ.get('BOT_TOKEN') or "YOUR_BOT_TOKEN_HERE"
ALLOWED_NUMBERS_FILE = os.environ.get('ALLOWED_NUMBERS_FILE', "/root/Telegram/TG_pre_bot_auth/phone_numbers.txt")
TEMP_PHONE_FILE = os.environ.get('TEMP_PHONE_FILE', "/root/Telegram/TG_pre_bot_auth/temp_phone_numbers.json")
MAIN_SCRIPT = os.environ.get('MAIN_SCRIPT', "magic")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Load allowed numbers ---
allowed_numbers = set()
if os.path.exists(ALLOWED_NUMBERS_FILE):
    with open(ALLOWED_NUMBERS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            number = line.strip()
            if number:
                allowed_numbers.add(number)
    logger.info(f"Allowed numbers loaded: {allowed_numbers}")
else:
    logger.warning(f"File {ALLOWED_NUMBERS_FILE} not found – allowed numbers list will be empty.")

def read_temp_numbers():
    if os.path.exists(TEMP_PHONE_FILE):
        try:
            with open(TEMP_PHONE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception as e:
            logger.error(f"Error reading temp numbers: {e}")
    return []

def normalize_number(phone: str) -> str:
    import re
    phone = re.sub(r"[\s\-()]", "", phone)
    if not phone.startswith("+"):
        phone = "+" + phone
    return phone

authorized_users = set()

app = Client(
    "pre_auth_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

@app.on_message(filters.private & ~filters.service)
def pre_auth_handler(client, message):
    user_id = message.from_user.id if message.from_user else None
    if user_id is None:
        return
    if user_id in authorized_users:
        return  # Уже авторизован
    # Если контакт — проверяем
    if message.contact:
        contact = message.contact
        if (contact.user_id == user_id) or (contact.user_id is None):
            phone = normalize_number(contact.phone_number)
            temp_data = read_temp_numbers()
            temp_numbers = {entry.get("phone") for entry in temp_data if isinstance(entry, dict)}
            if phone in allowed_numbers or phone in temp_numbers:
                authorized_users.add(user_id)
                message.reply_text("✅ Authorization successful! You can now use the bot.")
                message.reply_text("▶️ Continuing work...", reply_markup=ReplyKeyboardMarkup([], remove_keyboard=True))
                # Останавливаем Pyrogram и запускаем основной бот
                import threading
                threading.Thread(target=shutdown_and_run_magic, daemon=True).start()
                return
            else:
                message.reply_text("❌ Access denied. Your number was not found in the allowed list.")
                return
        else:
            message.reply_text("❗ Please send your own contact.")
            return
    # Если не авторизован и не контакт — просим контакт
    button = KeyboardButton("Share Contact ☎️", request_contact=True)
    reply_markup = ReplyKeyboardMarkup([[button]], one_time_keyboard=True, resize_keyboard=True)
    message.reply_text(
        "🔒 To use the bot, you must be authorized.\nPlease click the button below to share your contact.",
        reply_markup=reply_markup
    )
    return

def shutdown_and_run_magic():
    import time
    app.stop()
    time.sleep(1)
    logger.info(f"Launching main module {MAIN_SCRIPT}...")
    runpy.run_module(MAIN_SCRIPT, run_name="__main__")

if __name__ == "__main__":
    logger.info("Pre-auth bot started. Waiting for user authorization...")
    app.run()
