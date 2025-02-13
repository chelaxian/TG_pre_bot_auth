# TG Pre Bot Auth

This project adds a pre-authentication layer to your Telegram bot to ensure that only authorized users (i.e., those whose phone numbers are pre-approved) can access your bot’s functionality. It intercepts incoming updates and forces users to share their contact via Telegram’s built-in contact sharing method. If the user's phone number is found in the `phone_numbers.txt` file, the update is passed to the main bot logic (in `bot.py`); otherwise, the user is rejected.

## Features

- **Pre-Bot Authentication:** Intercepts every update before it reaches your main bot logic.
- **Secure Phone Verification:** Uses Telegram's contact sharing method to securely verify the user's phone number.
- **Allowed Numbers Check:** Compares the normalized phone number against a list of allowed numbers stored in `phone_numbers.txt`.
- **Seamless Integration:** Authorized updates are forwarded to your existing `bot.py` without any changes to its code.

## How It Works

1. **Allowed Numbers List:**  
   The script reads allowed phone numbers from `phone_numbers.txt` (one number per line in the format, e.g., `+79991112233`).

2. **Global Update Interception:**  
   It monkey-patches the `Application.process_update` method (from the `python-telegram-bot` library) so that every incoming update is checked for user authorization.

3. **Contact Verification:**  
   - If an update contains a contact, the phone number is normalized (removing spaces and dashes, ensuring it starts with a "+").
   - If the normalized number is found in the allowed list, the user is authorized and the update is forwarded to `bot.py`.
   - If the number is not in the allowed list, or if no contact is present, the bot responds with a request for the user to share their contact.

## Requirements

- Python 3.x
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [python-dotenv](https://github.com/theskumar/python-dotenv)

You can install the dependencies via pip:

```bash
pip install python-telegram-bot python-dotenv
```

## Setup and Usage

1. **Create a `.env` File:**  
   In the project root, create a file named `.env` and add your Telegram bot token:

   ```env
   BOT_TOKEN=your_bot_token_here
   ```

2. **Prepare the Allowed Numbers File:**  
   Create a file named `phone_numbers.txt` in the project root and add allowed phone numbers (one per line). For example:

   ```
   +79991112233
   +1234567890
   ```

3. **Ensure Your Bot Files Are Present:**  
   Make sure your project contains your main bot script (`bot.py`) and any configuration file (e.g., `config.py`) that your bot requires.

4. **Run the Authenticator:**  
   Instead of running your bot directly with `python3 bot.py`, run the pre-authentication layer:

   ```bash
   python3 authenticator.py
   ```

   The authenticator will start and intercept incoming updates. Only users who share an allowed phone number will have their updates passed to the main bot logic.

## Contributing

Feel free to open issues or submit pull requests if you have any improvements or bug fixes.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgements

This project was created to help secure Telegram bots by adding an additional pre-authentication layer, ensuring that only trusted users can access paid API services.

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

