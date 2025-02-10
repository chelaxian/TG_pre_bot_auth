# TG Pre Bot Auth

This project adds a pre-authentication layer to your Telegram bot to ensure that only authorized users (i.e., those whose phone numbers are pre-approved) can access your bot’s functionality. It intercepts incoming updates and forces users to share their contact via Telegram’s built-in contact sharing method. If the user's phone number is found in the `phone_numbers.txt` file, the update is passed to the main bot logic (in `bot.py`); otherwise, the user is rejected.

## Features

- **Pre-Bot Authentication:** Intercepts every update before it reaches your main bot logic.
- **Secure Phone Verification:** Uses Telegram's contact sharing method to securely verify the user's phone number.
- **Allowed Numbers Check:** Compares the normalized phone number against a list of allowed numbers stored in `phone_numbers.txt`.
- **Seamless Integration:** Authorized updates are forwarded to your existing `bot.py` without any changes to its code.

## How It Works

1. **Allowed Numbers List:**  
   The script reads allowed phone numbers from `phone_numbers.txt` (one number per line in the format, e.g., `+79262355196`).

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
