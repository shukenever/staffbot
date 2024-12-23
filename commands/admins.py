from telegram import Update
from telegram.ext import CallbackContext
from main import log_command, AUTHORIZED_USER_IDS
import json

def admins(update: Update, context: CallbackContext) -> None:
    log_command(update, context, 'admins')
    
    if update.message.from_user.id in AUTHORIZED_USER_IDS:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
            admins = config["admins"]

        if admins:
            update.message.reply_text("Admin user_ids: " + ', '.join(map(str, admins)), reply_to_message_id=update.message.message_id)
        else:
            update.message.reply_text("There are no admin user_ids.", reply_to_message_id=update.message.message_id)