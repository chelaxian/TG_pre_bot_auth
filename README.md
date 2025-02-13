# TG Pre Bot Auth

TG Pre Bot Auth is a pre-authentication layer for your Telegram bot. It intercepts every incoming update and forces users to share their contact via Telegram’s built-in contact sharing method. Only users whose normalized phone numbers are present in your allowed numbers file (and/or in the temporary numbers file) will have their updates passed on to the main bot logic.

Temporary phone numbers can also be used – these are stored in a JSON file along with a deletion date. This allows you to grant temporary access without permanently adding the number to your allowed list.

---

## Features

- **Pre-Bot Authentication:**  
  Intercepts every update before it reaches your main bot logic.

- **Secure Phone Verification:**  
  Uses Telegram's contact sharing method to securely verify the user's phone number.

- **Allowed Numbers Check:**  
  Compares the normalized phone number against a list of allowed numbers stored in a file.

- **Temporary Phone Numbers:**  
  Temporary numbers (with an associated deletion date) are stored in a separate JSON file and are also accepted for authorization.

- **Seamless Integration:**  
  Once a user is authorized, their updates are passed to your main bot script without any changes to its code.

---

## How It Works

- **Allowed Numbers List:**  
  The authenticator reads allowed phone numbers from a file (one number per line, e.g., `+79991112233`).

- **Temporary Numbers:**  
  It also reads temporary phone numbers from a JSON file. Each entry in this file should be an object with at least a `"phone"` key (and a `"deletion_date"` key, which is used to automatically expire the number).

- **Global Update Interception:**  
  It monkey-patches the `Application.process_update` method (from the python-telegram-bot library) so that every incoming update is checked for user authorization.

- **Contact Verification:**  
  If an update contains a contact, the phone number is normalized (removing spaces and dashes, ensuring it starts with a "+").  
  If the normalized number is found either in the allowed list or in the temporary numbers list, the user is authorized and their update is passed to the main bot logic.  
  If the number is not found (or if no contact is provided), the bot responds with a prompt to share a contact.

---

## Requirements

- Python 3.x
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [python-dotenv](https://github.com/theskumar/python-dotenv)

Install dependencies via pip:

```bash
pip install python-telegram-bot python-dotenv
```

---

## Setup and Usage

### Configuration

Edit the **CONFIGURATION** section at the top of `authenticator.py` or create a `.env` file in your project root with the following parameters:

- **BOT_TOKEN:**  
  The Telegram bot token. The token is preferably taken from the environment variable `BOT_TOKEN`. If not set, you can explicitly specify it here.  
  _Example (in .env file):_  
  `BOT_TOKEN=your_bot_token_here`

- **ALLOWED_NUMBERS_FILE:**  
  The path to the file that stores allowed (permanent) phone numbers. One phone number per line.  
  _Example:_  
  `/root/Telegram_bot/phone_numbers.txt`

- **TEMP_PHONE_FILE:**  
  The path to the JSON file that stores temporary phone numbers along with their deletion dates.  
  _Example:_  
  `/root/Telegram_bot/temp_phone_numbers.json`

- **MAIN_SCRIPT:**  
  The name (or path) of your main bot script (e.g., `bot`). The authenticator will run this script after authorizing a user.  
  _Example:_  
  `MAIN_SCRIPT=bot`

### Using Temporary Phone Numbers

You can grant temporary access by adding phone numbers to the temporary numbers file (`temp_phone_numbers.json`). Each entry in this file should be a JSON object with at least:

```json
{
  "phone": "+79991112233",
  "deletion_date": "2025-12-31T23:59:59"
}
```

Temporary numbers will be accepted for authorization along with permanent numbers, and they are displayed with a ⏳ icon and a label showing the approximate remaining lifetime.

---

## Running the Authenticator

Instead of running your main bot directly with, for example, `python3 bot.py`, run the pre-authentication layer:

```bash
python3 authenticator.py
```

The authenticator will intercept incoming updates and only pass those from authorized users (based on the allowed and temporary numbers) to your main bot logic.

---

## Contributing

Feel free to open issues or submit pull requests if you have any improvements or bug fixes.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---
---

# Admin Phone Bot

**Admin Phone Bot** is a Telegram bot designed to work exclusively with the administrator. It automatically adds phone numbers (from contacts or plain text messages) to a list, allows you to manage the list, and provides several administrative commands such as restarting and updating the bot. Additionally, the bot now supports temporary phone numbers with a defined lifetime.

---

## Features

### Get Your Telegram ID
- **/id** – The only command available to everyone. It returns your Telegram user ID in a monospace format for easy copying.

### Automatic Multiple Phone Number Addition
- If the bot receives a message containing one or several phone numbers (each on a separate line) — either via a contact or text — it normalizes and automatically adds all valid numbers to the list.

### Manage Phone Number List
- **/add `<phone>`** – Add a phone number to the permanent list.
- **/del `<phone>`** – Remove a phone number from both the permanent and temporary lists.
- **/list** – Display a paginated inline keyboard with all phone numbers from both permanent and temporary lists. Temporary numbers are marked with the ⏳ emoji and show the approximate remaining lifetime (e.g., `(< 1m)`, `(< 2h)`, `(< 6d)`, `(< 3w)`, `(< 5M)`, `(< 2Y)`, etc.). Navigation buttons allow you to browse pages, and a global **Cancel** button cancels deletion.

### Temporary Phone Number Addition
- **/temp `<duration>` `<phone>`** – Temporarily add a phone number.
  - The `<duration>` can be specified in seconds (e.g., `500s`), minutes (e.g., `100m`), days (e.g., `10d`), weeks (e.g., `2w`), months (e.g., `6M`), or years (e.g., `1Y`). 
  - The bot calculates the deletion date based on the current time and stores the temporary number along with its deletion date in a separate JSON file (`temp_phone_numbers.json`).
  - Temporary numbers appear at the top of the list in **/list** and are marked with ⏳.

### Search for a Phone Number
- **/find `<phone>`** – Search for a phone number in the combined permanent and temporary lists.
  - Displays a green check mark (✅) if the number is found, and a red cross (❌) if not.
  - If the number is temporary, an additional ⏳ symbol is shown.

### Deep Link Generation for Telegram Profiles
- **/tme [\<phone\>]** – Generate deep links in the t.me format.
  - Without an argument, it returns a list of deep links for all numbers (split into multiple messages if necessary).
  - With a specified `<phone>`, it returns the deep link for that phone only.
  - Format: `https://t.me/+<phone>`

- **/tg [\<phone\>]** – Generate deep links in the tg://resolve format.
  - Without an argument, it returns a list of deep links for all numbers (split into multiple messages if necessary).
  - With a specified `<phone>`, it returns the deep link for that phone only.
  - Format: `tg://resolve?phone=<phone_without_plus>`

### Administrative Commands
- **/restart** – Restart the bot by executing the restart script.
  ❗️DON'T FORGET TO RESTART YOUR BOT EVERY TIME YOUR ADD/DELETE PHONE NUMBER (TO REFRESH ACCESS)❗️
- **/update** – Update the bot by executing the update script. The update log is streamed in real time in the same message, and upon completion the log is cleared and replaced with a final message.
- **/help** – Display a help message with a formatted list of all available commands in a fixed-width code block.

### Access Restriction
- The bot processes commands only from the administrator whose Telegram user ID is specified in the configuration. All commands (except **/id**) are ignored for other users.

---

## Installation and Setup

### Requirements
- Python 3.7 or higher.
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) (version 20.x).
- [python-dotenv](https://github.com/theskumar/python-dotenv) (optional, for environment variables).
- Bash scripts for restarting and updating the bot (e.g., `restart_bot.sh` and `update_bot.sh`).
- [python-dateutil](https://pypi.org/project/python-dateutil/) (for duration calculations).

### Installation

1. **Create a Virtual Environment (optional but recommended):**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install Dependencies:**
   ```bash
   pip install python-telegram-bot python-dotenv python-dateutil
   ```

### Configuration

Edit the **CONFIGURATION** section at the top of the `admin_phone_bot.py` file:

- **BOT_TOKEN:** Enter your bot token (e.g., `"0000000000:XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"`).
- **ADMIN_ID:** Specify the Telegram user ID of the administrator (e.g., `123456789`).
- **PHONE_FILE:** Set the path to the file that stores permanent phone numbers (one per line).  
  Example: `/root/Telegram_bot/phone_numbers.txt`
- **TEMP_PHONE_FILE:** Set the path to the JSON file that stores temporary phone numbers along with their deletion dates.  
  Example: `/root/Telegram_bot/temp_phone_numbers.json`
- **RESTART_SCRIPT:** Set the path to the script that restarts the bot.  
  Example: `/root/Telegram_bot/restart_bot.sh`
- **UPDATE_SCRIPT:** Set the path to the script that updates the bot.  
  Example: `/root/Telegram_bot/update_bot.sh`
- **TEMP_CHECK_INTERVAL:** Set the check interval for temporary numbers (e.g., `"1h"`).

---

## Running the Bot

Start the bot with the following command:
```bash
python3 admin_phone_bot.py
```

The bot will now listen for messages and commands on Telegram. **Note:** It only accepts commands from the administrator (whose ID is set as **ADMIN_ID**).

---

## Available Commands

```
/add <phone>         - Add a phone number to the permanent list
/del <phone>         - Remove a phone number from both permanent and temporary lists
/list                - Show a paginated menu with phone numbers (temporary numbers are marked with ⏳ and show remaining lifetime)
/find <phone>        - Search for a phone number in the combined list (✅ if found, ❌ if not; temporary numbers show ⏳)
/temp <duration> <phone> - Temporarily add a phone number (e.g., /temp 500s, /temp 100m, /temp 10d, /temp 2w, /temp 6M, /temp 1Y)
/tme [<phone>]       - Show deep links in t.me format (if <phone> is provided, only that link is returned)
/tg [<phone>]        - Show deep links in tg://resolve format (if <phone> is provided, only that link is returned)
/restart             - Restart the bot using the restart script
/update              - Update the bot using the update script (logs are streamed in real time)
/help                - Display this help message
/id                  - Return your Telegram user ID (available to everyone)
```

> **Note:** The **/help** command displays the list of commands inside a fixed-width code block to ensure proper alignment.

---

## Usage Examples

- **Adding a Permanent Number:**
  ```
  /add +79991112233
  ```
  The bot adds the number to the permanent list if it isn’t already present.

- **Temporarily Adding a Number:**
  ```
  /temp 10d +79269269966
  ```
  The bot calculates the deletion date (10 days from now) and stores the temporary number in `temp_phone_numbers.json`. Temporary numbers appear at the top of the list with a ⏳ icon and a label like `(< 3d)`.

- **Removing a Number:**
  ```
  /del +79991112233
  ```
  The bot removes the number from both the permanent and temporary lists.

- **Listing Numbers:**
  ```
  /list
  ```
  The bot displays a paginated inline keyboard with phone numbers. Temporary numbers are marked with ⏳ and show the remaining lifetime (e.g., `(< 2h)`). Navigation buttons allow you to browse pages. A global **Cancel** button is provided to cancel deletion.

- **Searching for a Number:**
  ```
  /find +79991112233
  ```
  The bot replies with a green check (✅) if the number is found, or a red cross (❌) if it isn’t. Temporary numbers will include the ⏳ symbol.

- **Generating Deep Links:**
  - **/tme** – Outputs deep links like `https://t.me/+79991112233`.  
  - **/tg** – Outputs deep links like `tg://resolve?phone=79991112233`.
  - Adding an argument (e.g., `/tme +79991112233`) returns the link for that number only.

- **Restarting and Updating:**
  - **/restart** – Executes the restart script and shows its output.
  - **/update** – Executes the update script and streams the log output in real time; at the end, the log is cleared and replaced with “❕ Update finished.”

- **Getting Your Telegram ID:**
  ```
  /id
  ```
  This command returns your Telegram user ID in a monospace code block.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## Contributing and Support

If you have suggestions, fixes, or questions, please open an issue or submit a pull request in this repository.

