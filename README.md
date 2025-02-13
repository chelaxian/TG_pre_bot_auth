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

**Admin Phone Bot** is a Telegram bot designed to work exclusively with the administrator. It automatically adds phone numbers (from contacts or plain text messages) to a list, allows you to manage the list, and provides several administrative commands such as restarting and updating the bot.

## Features

- **Get your Telegram ID:**  
  - **/id** – The only command that is allowed for everyone. It gives you your Telegram ID.

- **Automatic Phone Number Addition:**  
  If the bot receives a message containing a phone number (either via a contact or a text that resembles a phone number), it normalizes the number and automatically adds it to the list if it is valid.

- **Manage Phone Number List:**  
  - **/add `<phone>`** – Add a phone number to the list.
  - **/del `<phone>`** – Remove a phone number from the list.
  - **/list** – Display an inline keyboard with all phone numbers. When you click on a number, a confirmation menu appears before deletion.

- **Search for a Phone Number:**  
  - **/find `<phone>`** – Search for a phone number in the list. The bot displays a green check mark (✅) if the number is found and a red cross (❌) if it is not.

- **Deep Link Generation for Telegram Profiles:**  
  - **/tme** – Show deep links in the format:  
    `https://t.me/+<phone>`
  - **/tg** – Show deep links in the format:  
    `tg://resolve?phone=<phone_without_plus>`

- **Administrative Commands:**  
  - **/restart** – Restart the bot by executing the restart script.
  - **/update** – Update the bot by executing the update script. The update log is streamed in real time in the same message.
  - **/help** – Display a help message with a list of all available commands in a fixed-width code block.

- **Access Restriction:**  
  The bot only processes messages from the administrator whose Telegram user ID is specified in the configuration.

## Installation and Setup

### Requirements

- Python 3.7 or higher.
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) (version 20.x).
- Bash scripts for restarting and updating the bot (for example, `restart_bots.sh` and `update_bots.sh`).

### Installation

1. **Create a Virtual Environment (optional but recommended):**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install Dependencies:**

   ```bash
   pip install python-telegram-bot python-dotenv
   ```

### Configuration

Edit the **CONFIGURATION** section at the top of the `admin_phone_bot.py` file:

- **BOT_TOKEN:** Enter your bot token (e.g., `"0000000000:XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"`).
- **ADMIN_ID:** Specify the Telegram user ID of the administrator (e.g., `123456789`).
- **PHONE_FILE:** Set the path to the file that stores phone numbers (one number per line).  
  Example: `/root/Telegram/USERS/phone_numbers.txt`
- **RESTART_SCRIPT:** Set the path to the script that restarts the bot.  
  Example: `/root/Telegram/BOTS/restart_bots.sh`
- **UPDATE_SCRIPT:** Set the path to the script that updates the bot.  
  Example: `/root/Telegram/BOTS/update_bots.sh`

### Running the Bot

Start the bot with the following command:

```bash
python3 admin_phone_bot.py
```

The bot will now listen for messages and commands on Telegram. **Note:** It only accepts commands from the administrator (whose ID is set as `ADMIN_ID`).

## Available Commands

```
/add <phone>    - Add a phone number to the list
/del <phone>    - Remove a phone number from the list
/list           - Show a menu with phone numbers (with confirmation before deletion)
/find <phone>   - Search for a phone number in the list (✅ if found, ❌ if not)
/tme            - Show deep links in t.me format
/tg             - Show deep links in tg://resolve format
/restart        - Restart the bot using the restart script
/update         - Update the bot using the update script (logs are streamed in real time)
/help           - Display this help message
```

> **Note:** The **/help** command displays the list of commands inside a fixed-width code block to ensure all text and hyphens are aligned.

## Usage Examples

- **Adding a Number:**  
  Send:  
  `/add +79991112233`  
  The bot will add the number to the list if it isn’t already present.

- **Removing a Number:**  
  Send:  
  `/del +79991112233`  
  Alternatively, use the **/list** command, select the number from the inline menu, and confirm deletion.

- **Searching for a Number:**  
  Send:  
  `/find +79991112233`  
  The bot replies with a green check (✅) if the number is found, or a red cross (❌) if it isn’t.

- **Generating Deep Links:**  
  - **/tme** – Outputs links like `https://t.me/+79991112233`.
  - **/tg** – Outputs links like `tg://resolve?phone=79991112233`.

- **Restarting the Bot:**  
  Send:  
  `/restart`  
  The bot executes the restart script and displays the output.

- **Updating the Bot:**  
  Send:  
  `/update`  
  The bot runs the update script and streams the log output in real time.

- **Displaying Help:**  
  Send:  
  `/help`  
  The bot will show a help message with a formatted list of all commands.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contributing and Support

If you have suggestions, fixes, or questions, please open an issue or submit a pull request in this repository.

