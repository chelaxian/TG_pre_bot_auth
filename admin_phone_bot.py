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
- /list          - Show a menu with phone numbers (with confirmation before deletion)
- /find <phone>  - Search for a phone number in the list (displays ✅ if found and ❌ if not)
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

# Paths to the shell scripts for restarting and updating the bot.
RESTART_SCRIPT = "/root/Telegram_bot/restart_bot.sh"
UPDATE_SCRIPT = "/root/Telegram_bot/update_bot.sh"

#############################
# CONFIGURATION
#############################

import os
import re
import subprocess
import logging
import asyncio

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
    /del <phone> - Remove a phone number from the list.
    """
    if not ADMIN_ID or update.effective_user.id != ADMIN_ID:
        return

    args = context.args
    if not args:
        await update.message.reply_text("❔ Usage: /del <phone number>")
        return

    phone = " ".join(args)
    phone = normalize_number(phone)
    numbers = read_phone_numbers()
    if phone in numbers:
        numbers.remove(phone)
        write_phone_numbers(numbers)
        await update.message.reply_text(f"➖ Removed phone number: {phone}")
    else:
        await update.message.reply_text(f"⚠️ {phone} not found in the list.")


async def list_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /list - Display an inline keyboard with phone numbers.
    Clicking on a button shows a confirmation menu before deletion.
    Additionally, a Cancel button is provided to exit the menu.
    """
    if not ADMIN_ID or update.effective_user.id != ADMIN_ID:
        return

    numbers = sorted(read_phone_numbers())
    if not numbers:
        await update.message.reply_text("⚠️ The list is empty.")
        return

    keyboard = []
    for num in numbers:
        # Callback data: "confirm|<phone>"
        keyboard.append([InlineKeyboardButton(num, callback_data=f"confirm|{num}")])
    # Add a global "Cancel" button to exit the list menu.
    keyboard.append([InlineKeyboardButton("🔙 Cancel", callback_data="cancel")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("❓ Select a phone number to delete:", reply_markup=reply_markup)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle inline keyboard button callbacks for deletion confirmation.
    """
    if not ADMIN_ID or update.effective_user.id != ADMIN_ID:
        return

    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("confirm|"):
        # Show confirmation menu
        phone = data.split("|", 1)[1]
        keyboard = [
            [
                InlineKeyboardButton("‼️ Yes, delete", callback_data=f"delete|{phone}"),
                InlineKeyboardButton("🔙 Cancel", callback_data=f"cancel|{phone}"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text=f"❓ Are you sure you want to delete {phone}?",
            reply_markup=reply_markup,
        )
    elif data.startswith("delete|"):
        phone = data.split("|", 1)[1]
        numbers = read_phone_numbers()
        if phone in numbers:
            numbers.remove(phone)
            write_phone_numbers(numbers)
            await query.edit_message_text(text=f"➖ Removed phone number: {phone}")
        else:
            await query.edit_message_text(text=f"⚠️ {phone} not found in the list.")
    elif data.startswith("cancel|"):
        phone = data.split("|", 1)[1]
        await query.edit_message_text(text=f"🔚 Deletion cancelled for {phone}.")
    elif data == "cancel":
        await query.edit_message_text(text="🔚 Deletion cancelled.")



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


async def find_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /find <phone> - Search for a phone number in the list.
    Displays a green check mark if found and a red cross if not.
    """
    if not ADMIN_ID or update.effective_user.id != ADMIN_ID:
        return

    args = context.args
    if not args:
        await update.message.reply_text("❔ Usage: /find <phone number>")
        return

    phone = " ".join(args)
    phone = normalize_number(phone)
    numbers = read_phone_numbers()
    if phone in numbers:
        await update.message.reply_text(f"✅ {phone} is in the list.")
    else:
        await update.message.reply_text(f"❌ {phone} not found in the list.")


async def tme_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /tme - Output a list of deep links in t.me format.
    Format: https://t.me/+<phone>
    """
    if not ADMIN_ID or update.effective_user.id != ADMIN_ID:
        return

    numbers = sorted(read_phone_numbers())
    if not numbers:
        await update.message.reply_text("⚠️ The list is empty.")
        return

    links = []
    for num in numbers:
        links.append(f"https://t.me/{num}")
    await update.message.reply_text("\n".join(links))


async def tg_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /tg - Output a list of deep links in tg://resolve format.
    Format: tg://resolve?phone=<phone_without_plus>
    """
    if not ADMIN_ID or update.effective_user.id != ADMIN_ID:
        return

    numbers = sorted(read_phone_numbers())
    if not numbers:
        await update.message.reply_text("⚠️ The list is empty.")
        return

    links = []
    for num in numbers:
        plain = num[1:] if num.startswith("+") else num
        links.append(f"tg://resolve?phone={plain}")
    await update.message.reply_text("\n".join(links))


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
        "/add &lt;phone&gt;    - Add a phone number to the list\n"
        "/del &lt;phone&gt;    - Remove a phone number from the list\n"
        "/list           - Show a menu with phone numbers (with confirmation before deletion)\n"
        "/find &lt;phone&gt;   - Search for a phone number in the list\n"
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


# --- Handler for non-command messages (auto-add phone) ---
async def phone_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Non-command messages handler.
    If the message contains phone numbers (via contact or text),
    automatically add them to the list. Multiple numbers (one per line) are supported.
    If any line does not represent a valid phone number, it is reported.
    """
    if not ADMIN_ID or update.effective_user.id != ADMIN_ID:
        return

    message = update.effective_message

    # If message contains a contact, process it normally
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

    # Process text message: split by lines and process each line
    text = message.text or ""
    lines = text.splitlines()
    if not lines:
        await message.reply_text("⚠️ No phone number detected in your message.")
        return

    # Read current phone numbers once
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

    # Write updated numbers if any were added
    if added_numbers:
        write_phone_numbers(numbers)

    # Build response message
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

    # Set bot commands on startup
    async def on_startup(app: Application):
        await set_bot_commands(app)
        logger.info("Bot commands set.")

    application.post_init = on_startup

    # Run the bot
    application.run_polling()


if __name__ == "__main__":
    main()
