# TG_pre_bot_auth
Add file `authenticator.py` and `phone_numbers.txt` into your project folder and run `Python3 authenticator.py` instead of `Python3 bot.py`

---

This python script adds pre-bot authentication layer.
It forces users to send their's phone number via Telegram contact exchange method,
Checks if phone number exist in `phone_numbers.txt` (you have to already filled in this file) and if so - proxy pass users to original `bot.py` functional. And reject all other unauthenticated users.
