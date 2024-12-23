from telegram import Update
from telegram.ext import CallbackContext
from main import log_command, PRIVATE_GROUP_CHAT_ID
import json

def help(update: Update, context: CallbackContext) -> None:
    log_command(update, context, 'help')
    
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    admins = config["admins"]

    if update.message.chat_id == PRIVATE_GROUP_CHAT_ID:
        if str(update.message.from_user.id) in admins:
            try:
                ordermsg = (
                "*/invoice <invoice_id>* - Lookup an invoice\n"
                "*/invoices <email>* - Get all invoices from an email\n"
                "*/resend <email> <invoice_id>* - Resend the order mail\n"
                "*/process <invoice_id>* - Manual complete an order\n"
                "*/replace <part invoice id> <quantity>* - Replace an order\n"
                "*/info <email>* - Display customer info by email\n"
                "*/add_balance <customer id> <amount>* - Add balance\n"
                "*/remove_balance <customer id> <amount>* - Remove balance\n"
                "*/admins* - Displays admins user\_id\n"
                "*/add_admin <user_id>* - add admin user\_id\n"
                "*/remove_admin <user_id>* - remove admin user\_id\n"
                "*/blacklist <email>* - blacklists customer email and IP")
                update.message.reply_text(ordermsg, parse_mode='Markdown')
            except Exception as e:
                print('An unexpected error occurred: {e}')