from telegram import Update
from telegram.ext import CallbackContext
from main import log_command, AUTHORIZED_USER_IDS
import json

def add_admin(update: Update, context: CallbackContext) -> None:
    log_command(update, context, 'add_admin')
    
    if update.message.from_user.id in AUTHORIZED_USER_IDS:
        parts = update.message.text.split(" ")
        if len(parts) == 2:
            user_id = str(parts[1])
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
                admins = config["admins"]

            if user_id not in admins:
                admins.append(user_id)
                with open("config.json", "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=4)
                update.message.reply_text(f"User {user_id} has been added as an admin.", reply_to_message_id=update.message.message_id)
            else:
                update.message.reply_text(f"User {user_id} is already an admin.", reply_to_message_id=update.message.message_id)
        else:
            update.message.reply_text("Please provide a user_id to add as an admin.", reply_to_message_id=update.message.message_id)