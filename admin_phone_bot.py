#!/usr/bin/env python3
"""
Admin Phone Bot

This Telegram bot is designed to work exclusively with the administrator.
It manages a list of allowed phone numbers stored in a file and provides
the following features:

- Automatically adds a phone number (from a contact or plain text) to the list,
  if it is valid.
- /add <phone>   - Add a phone number to the list
- /del <phone>   - Remove a phone number from the list
- /list          - Show a menu with phone numbers (with confirmation before deletion).
                  Temporary numbers are marked with ⏳.
- /find <phone>  - Search for a phone number in the list (displays ✅ if found and ❌ if not)
- /temp <duration> <phone> - Temporarily add a phone number.
- /tme           - Show deep links in t.me format
- /tg            - Show deep links in tg://resolve format
- /restart       - Restart the bot using the restart script
- /update        - Update the bot using the update script (streaming output in real time)
- /help          - Display help message
- /id            - Return your Telegram user ID (available to all users)

All configuration values are defined in the CONFIGURATION section below.
"""

#############################
# CONFIGURATION
#############################

# Bot token – you can either set it here or load it from the environment.
BOT_TOKEN = "0000000000:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"

# Telegram user ID of the administrator (only messages from this user are processed for all commands except /id)
ADMIN_ID = 1234567

# Path to the file that stores allowed phone numbers (one per line)
PHONE_FILE = "/root/Telegram_bot/phone_numbers.txt"

# Path to the file that stores temporary phone numbers (list of dicts with keys "phone" and "deletion_date")
TEMP_PHONE_FILE = "/root/Telegram_bot/temp_phone_numbers.json"

# Paths to the shell scripts for restarting and updating the bot.
RESTART_SCRIPT = "/root/Telegram_bot/restart_bot.sh"
UPDATE_SCRIPT = "/root/Telegram_bot/update_bot.sh"

# Check interval for temporary phone expiration.
# Format: a duration string (e.g. "1h", "1d", etc.).
TEMP_CHECK_INTERVAL = "1m"

# (Optional) Draft text for deep links (if needed; otherwise leave empty)
DRAFT_TEXT = ""  # currently not appended in deep links

#############################
# END CONFIGURATION
#############################

import os
import re
import math
import subprocess
import logging
import asyncio
import json
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    BotCommand
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def normalize_number(phone: str) -> str:
    """
    Remove spaces, dashes, and parentheses and ensure the number starts with a plus.
    """
    phone = re.sub(r"[\s\-()]", "", phone)
    if not phone.startswith("+"):
        phone = "+" + phone
    return phone


def is_valid_phone(phone: str) -> bool:
    """
    Check if the phone number matches the pattern: a plus sign followed by 7 to 15 digits.
    """
    return bool(re.fullmatch(r"\+\d{7,15}", phone))


def read_phone_numbers() -> set:
    """
    Read phone numbers from PHONE_FILE and return a set.
    """
    numbers = set()
    if os.path.exists(PHONE_FILE):
        with open(PHONE_FILE, "r", encoding="utf-8") as f:
            for line in f:
                num = line.strip()
                if num:
                    numbers.add(num)
    return numbers


def write_phone_numbers(numbers: set):
    """
    Overwrite PHONE_FILE with the provided set of phone numbers.
    """
    with open(PHONE_FILE, "w", encoding="utf-8") as f:
        for num in sorted(numbers):
            f.write(num + "\n")


def read_temp_numbers() -> list:
    """
    Read temporary phone numbers from TEMP_PHONE_FILE.
    Returns a list of dicts with keys "phone" and "deletion_date" (ISO format).
    """
    if os.path.exists(TEMP_PHONE_FILE):
        with open(TEMP_PHONE_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                if isinstance(data, list):
                    return data
            except json.JSONDecodeError:
                return []
    return []


def write_temp_numbers(data: list):
    """
    Write the list of temporary phone numbers to TEMP_PHONE_FILE.
    """
    with open(TEMP_PHONE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def parse_duration(duration_str: str):
    """
    Parse a duration string in the format number+unit.
    Allowed units: s, m, h, d, w, M, Y.
    The overall duration must not exceed 100 years.
    Returns a timedelta for s, m, h, d, w and a relativedelta for M and Y.
    """
    match = re.fullmatch(r"(\d+)([smhdwMY])", duration_str)
    if not match:
        raise ValueError("Invalid duration format. Use number+unit (e.g., 1d, 3600s).")
    value, unit = match.groups()
    value = int(value)
    if unit == "s":
        dur = timedelta(seconds=value)
    elif unit == "m":
        dur = timedelta(minutes=value)
    elif unit == "h":
        dur = timedelta(hours=value)
    elif unit == "d":
        dur = timedelta(days=value)
    elif unit == "w":
        dur = timedelta(weeks=value)
    elif unit == "M":
        dur = relativedelta(months=value)
    elif unit == "Y":
        dur = relativedelta(years=value)
    else:
        raise ValueError("Unsupported time unit.")

    max_duration = timedelta(days=100*365)
    if isinstance(dur, timedelta):
        if dur > max_duration:
            raise ValueError("Duration exceeds maximum allowed (100 years).")
    else:
        # For relativedelta, approximate total days:
        total_days = (dur.years or 0) * 365 + (dur.months or 0) * 30 + (dur.days or 0)
        if total_days > 100 * 365:
            raise ValueError("Duration exceeds maximum allowed (100 years).")
    return dur


def parse_check_interval(interval_str: str) -> timedelta:
    """
    Parse the TEMP_CHECK_INTERVAL string into a timedelta.
    For units s, m, h, d, w it returns a timedelta.
    For M or Y, approximate using 30 days for month and 365 days for year.
    """
    match = re.fullmatch(r"(\d+)([smhdwMY])", interval_str)
    if not match:
        raise ValueError("Invalid check interval format.")
    value, unit = match.groups()
    value = int(value)
    if unit == "s":
        return timedelta(seconds=value)
    elif unit == "m":
        return timedelta(minutes=value)
    elif unit == "h":
        return timedelta(hours=value)
    elif unit == "d":
        return timedelta(days=value)
    elif unit == "w":
        return timedelta(weeks=value)
    elif unit == "M":
        return timedelta(days=30 * value)
    elif unit == "Y":
        return timedelta(days=365 * value)
    else:
        raise ValueError("Unsupported time unit in check interval.")

def leftover_label(deletion_date_str: str) -> str:
    """
    Takes a deletion date (ISO string) and returns a short label showing the approximate
    remaining time in one of the units s, m, h, d, w, M, Y.
    It chooses the smallest unit where the ceiling value is between 1 and 9.
    For example:
      - 30 sec  →  (< 1s)  if < 1 second is not practical, you might consider it as (< 1m)
      - 70 sec  →  (< 2m)
      - 4000 sec → (< 2h)
      - 500000 sec → (< 6d)
    If the leftover time exceeds 9 years, returns "(> 9Y)".
    """
    try:
        deletion_date = datetime.fromisoformat(deletion_date_str)
    except Exception:
        return ""
    now = datetime.now()
    leftover = (deletion_date - now).total_seconds()
    if leftover <= 0:
        return ""
    # Определяем единицы измерения: (symbol, factor in seconds)
    units = [
        ("s", 1),
        ("m", 60),
        ("h", 3600),
        ("d", 86400),
        ("w", 604800),      # 7 days
        ("M", 2592000),     # 30 days
        ("Y", 31536000)     # 365 days
    ]
    for symbol, factor in units:
        val = leftover / factor
        ceil_val = math.ceil(val)
        if ceil_val <= 9:
            return f"(< {ceil_val}{symbol})"
    return "(> 9Y)"


# --- Command Handlers (admin-only, except /id) ---

async def add_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /add <phone> - Add a phone number to the list.
    """
    if not ADMIN_ID or update.effective_user.id != ADMIN_ID:
        return

    args = context.args
    if not args:
        await update.message.reply_text("❔ Usage: /add <phone number>")
        return

    phone = " ".join(args)
    phone = normalize_number(phone)
    if not is_valid_phone(phone):
        await update.message.reply_text("⚠️ Invalid phone number format.")
        return

    numbers = read_phone_numbers()
    if phone in numbers:
        await update.message.reply_text(f"⚠️ {phone} is already in the list.")
    else:
        numbers.add(phone)
        write_phone_numbers(numbers)
        await update.message.reply_text(f"➕ Added phone number: {phone}")


async def del_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /del <phone> - Remove a phone number from both permanent and temporary lists.
    """
    if not ADMIN_ID or update.effective_user.id != ADMIN_ID:
        return

    args = context.args
    if not args:
        await update.message.reply_text("❔ Usage: /del <phone number>")
        return

    phone = " ".join(args)
    phone = normalize_number(phone)
    perm_numbers = read_phone_numbers()
    temp_numbers = read_temp_numbers()  # список словарей с ключами "phone" и "deletion_date"

    removed_sources = []

    # Удаляем из постоянного списка, если найден
    if phone in perm_numbers:
        perm_numbers.remove(phone)
        write_phone_numbers(perm_numbers)
        removed_sources.append("permanent")

    # Удаляем из временного списка, если найден
    new_temp = []
    temp_removed = False
    for entry in temp_numbers:
        if entry.get("phone") == phone:
            temp_removed = True
        else:
            new_temp.append(entry)
    if temp_removed:
        write_temp_numbers(new_temp)
        removed_sources.append("temporary")

    if not removed_sources:
        await update.message.reply_text(f"⚠️ {phone} not found in the list.")
    else:
        sources = " and ".join(removed_sources)
        await update.message.reply_text(f"➖ Removed {phone} from {sources} list(s).")

            
# В обработчике кнопок (button_handler) необходимо добавить поддержку "page|":
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle inline keyboard button callbacks for deletion confirmation and pagination.
    """
    if not ADMIN_ID or update.effective_user.id != ADMIN_ID:
        return

    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("confirm|"):
        phone = data.split("|", 1)[1]
        temp_list = read_temp_numbers()
        deletion_date_str = ""
        for entry in temp_list:
            if entry.get("phone") == phone:
                dd = entry.get("deletion_date")
                if dd:
                    deletion_date_str = f"\nDeletion date: {dd}"
                break
        keyboard = [
            [
                InlineKeyboardButton("‼️ Yes, delete", callback_data=f"delete|{phone}"),
                InlineKeyboardButton("Back", callback_data="back_to_list"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = f"❓ Are you sure you want to delete {phone}?{deletion_date_str}"
        await query.edit_message_text(text=text, reply_markup=reply_markup)

    elif data.startswith("delete|"):
        phone = data.split("|", 1)[1]
        removed_sources = []
        # Remove from permanent list
        perm_numbers = read_phone_numbers()
        if phone in perm_numbers:
            perm_numbers.remove(phone)
            write_phone_numbers(perm_numbers)
            removed_sources.append("permanent")
        # Remove from temporary list
        temp_numbers = read_temp_numbers()
        new_temp = []
        temp_removed = False
        for entry in temp_numbers:
            if entry.get("phone") == phone:
                temp_removed = True
            else:
                new_temp.append(entry)
        if temp_removed:
            write_temp_numbers(new_temp)
            removed_sources.append("temporary")
        if removed_sources:
            sources = " and ".join(removed_sources)
            await query.edit_message_text(text=f"➖ Removed phone number: {phone} from {sources} list(s).")
        else:
            await query.edit_message_text(text=f"⚠️ {phone} not found in the list.")

    elif data == "back_to_list":
        await list_numbers(update, context, use_query=True)

    elif data == "cancel_main":
        await query.edit_message_text(text="🔚 Deletion cancelled.")

    elif data.startswith("page|"):
        page = int(data.split("|", 1)[1])
        new_markup = build_list_keyboard(page=page, page_size=10)
        await query.edit_message_reply_markup(reply_markup=new_markup)

    elif data == "cancel":
        await query.edit_message_text(text="🔚 Deletion cancelled.")

    else:
        logger.info(f"Unknown callback_data received: {data}")

        

async def restart_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /restart - Execute the restart script and return its output.
    """
    if not ADMIN_ID or update.effective_user.id != ADMIN_ID:
        return

    try:
        result = subprocess.run(
            [RESTART_SCRIPT],
            capture_output=True,
            text=True,
            check=True,
        )
        output = result.stdout.strip() or "❕ Service restarted"
        await update.message.reply_text(output)
    except subprocess.CalledProcessError as e:
        await update.message.reply_text(f"⚠️ Error restarting bot: {e}")


async def update_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /update - Execute the update script and stream its output in real time.
    The output is continuously updated in the same message, but only every update_interval seconds
    to avoid flooding Telegram.
    In the end, the log is cleared and a final message "❕ Update finished." is displayed.
    """
    if not ADMIN_ID or update.effective_user.id != ADMIN_ID:
        return

    sent_message = await update.message.reply_text("❕ Starting update...\n")
    
    process = await asyncio.create_subprocess_exec(
        UPDATE_SCRIPT,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT
    )
    
    accumulated_output = ""
    update_interval = 1.0  # update message once per second
    last_update_time = asyncio.get_event_loop().time()
    
    while True:
        line = await process.stdout.readline()
        if not line:
            break
        decoded_line = line.decode("utf-8")
        accumulated_output += decoded_line

        now = asyncio.get_event_loop().time()
        if now - last_update_time >= update_interval:
            last_update_time = now
            text_to_send = accumulated_output[-4000:]  # only last 4000 characters
            try:
                await sent_message.edit_text(text_to_send)
            except Exception as e:
                logger.error("Error editing message: %s", e)
            await asyncio.sleep(0.1)
    
    await process.wait()
    try:
        # Clear the log and display the final message
        await sent_message.edit_text("❕ Update finished.")
    except Exception as e:
        logger.error("Error editing final message: %s", e)

def split_text(text, chunk_size=4096):
    """Split text into chunks of at most chunk_size characters."""
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

def build_list_keyboard(page: int, page_size: int = 10):
    """
    Build an inline keyboard for a paginated /list command.
    Temporary numbers (from temp_phone_numbers.json) are placed at the beginning and marked with ⏳
    along with a short leftover time label.
    Navigation buttons "Prev" and "Next" are added if necessary, plus a global "Cancel" button.
    """
    # Получаем временные номера как словарь: phone -> deletion_date
    temp_entries = read_temp_numbers()  # list of dicts with "phone" and "deletion_date"
    temp_dict = {entry["phone"]: entry.get("deletion_date") for entry in temp_entries}
    
    # Получаем постоянные номера и исключаем временные
    perm_numbers = read_phone_numbers().difference(set(temp_dict.keys()))
    temp_numbers = sorted(temp_dict.keys())
    perm_numbers = sorted(perm_numbers)
    
    # Объединяем: временные номера первыми, затем постоянные
    combined = temp_numbers + perm_numbers

    total = len(combined)
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    page = max(1, min(page, total_pages))
    start = (page - 1) * page_size
    end = start + page_size
    page_items = combined[start:end]

    keyboard = []
    for num in page_items:
        if num in temp_dict:
            label = leftover_label(temp_dict[num])
            display_text = f"⏳ {num} {label}" if label else f"⏳ {num}"
        else:
            display_text = num
        keyboard.append([InlineKeyboardButton(display_text, callback_data=f"confirm|{num}")])
    
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(f"« Prev ({page-1}/{total_pages})", callback_data=f"page|{page-1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(f"Next ({page+1}/{total_pages}) »", callback_data=f"page|{page+1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Глобальная кнопка Cancel
    keyboard.append([InlineKeyboardButton("🔚 Cancel", callback_data="cancel_main")])
    return InlineKeyboardMarkup(keyboard)


async def list_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE, use_query: bool = False, page: int = 1):
    """
    /list - Display a paginated inline keyboard with phone numbers from both permanent and temporary lists.
    Temporary numbers are marked with ⏳ along with a short leftover time label.
    A global "Cancel" button is provided to cancel the deletion.
    """
    if not ADMIN_ID or update.effective_user.id != ADMIN_ID:
        return

    reply_markup = build_list_keyboard(page=page, page_size=10)
    text = "❓ Select a phone number to delete:"
    if use_query and update.callback_query:
        await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)
        
    
async def find_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /find <phone> - Search for a phone number in the combined list.
    Displays a green check mark if found and a red cross if not.
    If found in the temporary list, appends ⏳.
    """
    if not ADMIN_ID or update.effective_user.id != ADMIN_ID:
        return

    args = context.args
    if not args:
        await update.message.reply_text("❔ Usage: /find <phone number>")
        return

    phone = " ".join(args)
    phone = normalize_number(phone)
    perm_numbers = read_phone_numbers()
    temp_numbers = {entry.get("phone") for entry in read_temp_numbers()}
    combined = perm_numbers.union(temp_numbers)
    if phone in combined:
        response = f"✅ {phone}"
        if phone in temp_numbers:
            response += " ⏳"
        response += " is in the list."
    else:
        response = f"❌ {phone} not found in the list."
    await update.message.reply_text(response)


async def tme_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /tme [<phone>] - Output deep links in t.me format.
    If a phone number is specified, returns the link for that number.
    Otherwise, returns a list of deep links from the combined list.
    Format: https://t.me/+<phone>
    """
    if not ADMIN_ID or update.effective_user.id != ADMIN_ID:
        return

    perm_numbers = read_phone_numbers()
    temp_numbers = {entry.get("phone") for entry in read_temp_numbers()}
    combined = sorted(perm_numbers.union(temp_numbers))
    
    if context.args:
        phone = " ".join(context.args)
        phone = normalize_number(phone)
        link = f"https://t.me/{phone}"
        await update.message.reply_text(link)
    else:
        links = []
        for num in combined:
            links.append(f"https://t.me/{num}")
        full_text = "\n".join(links)
        for chunk in split_text(full_text, 4096):
            await update.message.reply_text(chunk)

async def tg_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /tg [<phone>] - Output deep links in tg://resolve format.
    If a phone number is specified, returns the link for that number.
    Otherwise, returns a list of deep links from the combined list.
    Format: tg://resolve?phone=<phone_without_plus>
    """
    if not ADMIN_ID or update.effective_user.id != ADMIN_ID:
        return

    perm_numbers = read_phone_numbers()
    temp_numbers = {entry.get("phone") for entry in read_temp_numbers()}
    combined = sorted(perm_numbers.union(temp_numbers))
    
    if context.args:
        phone = " ".join(context.args)
        phone = normalize_number(phone)
        plain = phone[1:] if phone.startswith("+") else phone
        link = f"tg://resolve?phone={plain}"
        await update.message.reply_text(link)
    else:
        links = []
        for num in combined:
            plain = num[1:] if num.startswith("+") else num
            links.append(f"tg://resolve?phone={plain}")
        full_text = "\n".join(links)
        for chunk in split_text(full_text, 4096):
            await update.message.reply_text(chunk)
        
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /help - Display help with a list of available commands.
    The commands are shown in a fixed-width code block.
    """
    if not ADMIN_ID or update.effective_user.id != ADMIN_ID:
        return

    help_text = (
        "<pre>\n"
        "Available commands:\n"
        "-------------------\n"
        "/add            - Add a phone number to the list\n"
        "/temp           - Temporarily add a phone number\n"
        "/del            - Remove a phone number from the list\n"
        "/list           - Show a menu with phone numbers (deletion)\n"
        "/find           - Search for a phone number in the list\n"
        "/tme            - Show deep links in t.me format\n"
        "/tg             - Show deep links in tg://resolve format\n"
        "/restart        - Restart the bot using the restart script\n"
        "/update         - Update the bot using the update script\n"
        "/help           - Display this help message\n"
        "/id             - Get your Telegram ID\n"
        "</pre>"
    )
    await update.message.reply_text(help_text, parse_mode="HTML")


# --- Command Handler for /id (available to everyone) ---
async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /id - Return your Telegram user ID in monospace format.
    This command is available to all users.
    """
    user = update.effective_user
    if user:
        await update.message.reply_text(f"Your Telegram ID: `{user.id}`", parse_mode="MarkdownV2")
    else:
        await update.message.reply_text("Unable to determine your Telegram ID.")


# --- Command Handler for /temp (temporary addition) ---
async def temp_number_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /temp <duration> <phone> - Temporarily add a phone number.
    Example: /temp 1d +79262355196 or /temp 3600s 79262355196
    The temporary phone number is stored along with its calculated deletion date.
    """
    if not ADMIN_ID or update.effective_user.id != ADMIN_ID:
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text("❔ Usage: /temp <duration> <phone number>\nExamples: 500s, 100m, 10d, 2w, 6M, 1Y")
        return

    duration_str = args[0]
    phone = " ".join(args[1:])
    try:
        duration = parse_duration(duration_str)
    except ValueError as e:
        await update.message.reply_text(f"⚠️ {e}")
        return

    phone = normalize_number(phone)
    if not is_valid_phone(phone):
        await update.message.reply_text("⚠️ Invalid phone number format.")
        return

    now = datetime.now()
    if isinstance(duration, timedelta):
        deletion_date = now + duration
    else:
        deletion_date = now + duration  # works with relativedelta

    deletion_date_str = deletion_date.isoformat()
    temp_numbers = read_temp_numbers()
    for entry in temp_numbers:
        if entry.get("phone") == phone:
            await update.message.reply_text(f"⚠️ {phone} is already temporarily added until {entry.get('deletion_date')}.")
            return
    temp_numbers.append({"phone": phone, "deletion_date": deletion_date_str})
    write_temp_numbers(temp_numbers)
    await update.message.reply_text(f"⏳ Temporarily added {phone} until {deletion_date_str}.")


# --- Background task to check temporary numbers expiration ---
async def check_temp_numbers():
    check_interval = parse_check_interval(TEMP_CHECK_INTERVAL)
    while True:
        try:
            temp_numbers = read_temp_numbers()
            now = datetime.now()
            updated = False
            new_list = []
            for entry in temp_numbers:
                deletion_date_str = entry.get("deletion_date")
                try:
                    deletion_date = datetime.fromisoformat(deletion_date_str)
                except Exception:
                    new_list.append(entry)
                    continue
                if now < deletion_date:
                    new_list.append(entry)
                else:
                    logger.info("Temporary number %s expired and removed.", entry.get("phone"))
                    updated = True
            if updated:
                write_temp_numbers(new_list)
        except Exception as e:
            logger.error("Error checking temporary numbers: %s", e)
        await asyncio.sleep(check_interval.total_seconds())


# --- Handler for non-command messages (auto-add phone) ---
async def phone_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Non-command messages handler.
    If the message contains phone numbers (via contact or text),
    automatically add them to the list. Multiple numbers (one per line) are supported.
    If any line is invalid, it is reported.
    """
    if not ADMIN_ID or update.effective_user.id != ADMIN_ID:
        return

    message = update.effective_message

    if message.contact:
        phone = message.contact.phone_number
        phone_norm = normalize_number(phone)
        if is_valid_phone(phone_norm):
            numbers = read_phone_numbers()
            if phone_norm in numbers:
                await message.reply_text(f"⚠️ {phone_norm} is already in the list.")
            else:
                numbers.add(phone_norm)
                write_phone_numbers(numbers)
                await message.reply_text(f"➕ Added phone number: {phone_norm}")
        else:
            await message.reply_text("⚠️ The provided contact does not seem to be a valid phone number.")
        return

    text = message.text or ""
    lines = text.splitlines()
    if not lines:
        await message.reply_text("⚠️ No phone number detected in your message.")
        return

    numbers = read_phone_numbers()
    added_numbers = []
    already_present = []
    invalid_numbers = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        phone_norm = normalize_number(line)
        if is_valid_phone(phone_norm):
            if phone_norm in numbers:
                already_present.append(phone_norm)
            else:
                numbers.add(phone_norm)
                added_numbers.append(phone_norm)
        else:
            invalid_numbers.append(line)

    if added_numbers:
        write_phone_numbers(numbers)

    responses = []
    if added_numbers:
        responses.append("➕ Added phone number(s): " + ", ".join(added_numbers))
    if already_present:
        responses.append("⚠️ Already in the list: " + ", ".join(already_present))
    if invalid_numbers:
        responses.append("❌ Invalid phone number format: " + ", ".join(invalid_numbers))

    if responses:
        await message.reply_text("\n".join(responses))
    else:
        await message.reply_text("⚠️ No valid phone numbers detected in your message.")


async def set_bot_commands(app: Application):
    """
    Set bot commands so that they are automatically available in Telegram.
    """
    commands = [
        BotCommand("add", "Add a phone number to the list"),
        BotCommand("del", "Remove a phone number from the list"),
        BotCommand("list", "Show phone numbers with deletion options"),
        BotCommand("find", "Search for a phone number in the list"),
        BotCommand("temp", "Temporarily add a phone number"),
        BotCommand("tme", "Show deep links (t.me format)"),
        BotCommand("tg", "Show deep links (tg://resolve format)"),
        BotCommand("restart", "Restart the bot using the restart script"),
        BotCommand("update", "Update the bot using the update script"),
        BotCommand("help", "Display help message"),
        BotCommand("id", "Get your Telegram user ID"),
    ]
    await app.bot.set_my_commands(commands)


def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Register command handlers (admin-only)
    application.add_handler(CommandHandler("add", add_number))
    application.add_handler(CommandHandler("del", del_number))
    application.add_handler(CommandHandler("list", list_numbers))
    application.add_handler(CommandHandler("find", find_number))
    application.add_handler(CommandHandler("temp", temp_number_command))
    application.add_handler(CommandHandler("tme", tme_links))
    application.add_handler(CommandHandler("tg", tg_links))
    application.add_handler(CommandHandler("restart", restart_bot))
    application.add_handler(CommandHandler("update", update_bot))
    application.add_handler(CommandHandler("help", help_command))
    
    # Register /id command handler (available to everyone)
    application.add_handler(CommandHandler("id", id_command))

    # Handler for inline button callbacks (for deletion confirmation)
    application.add_handler(CallbackQueryHandler(button_handler))

    # Handler for non-command messages (auto-add phone)
    application.add_handler(MessageHandler(filters.ALL & (~filters.COMMAND), phone_message))

    async def on_startup(app: Application):
        await set_bot_commands(app)
        logger.info("Bot commands set.")
        # Start background task to check temporary numbers
        asyncio.create_task(check_temp_numbers())

    application.post_init = on_startup

    application.run_polling()


if __name__ == "__main__":
    main()
