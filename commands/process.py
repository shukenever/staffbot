from telegram import Update
from telegram.ext import CallbackContext
from main import log_command, PRIVATE_GROUP_CHAT_ID
import json, requests

def process(update: Update, context: CallbackContext) -> None:
    log_command(update, context, 'process')
    
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    admins = config["admins"]

    if update.message.chat_id == PRIVATE_GROUP_CHAT_ID:
        if str(update.message.from_user.id) in admins:
            try:
                parts = update.message.text.split(" ")
                if len(parts) == 2:
                    invoice_id = str(parts[1])
                    
                    processss = processs(invoice_id)
                    update.message.reply_text(processss, reply_to_message_id=update.message.message_id)
                else:
                    update.message.reply_text("Invalid format: /process <invoice_id>", reply_to_message_id=update.message.message_id)
            except Exception as e:
                print(f"An error occurred: {e}")


def processs(invoice_id):
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
        API_key = config["api_key"]
        shop = config["shop_id"]

    url = f'https://dev.sellpass.io/self/{shop}/invoices/{invoice_id}/process'

    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer '+API_key
        }

    try:
        response = requests.post(url, headers=headers)

        if response.status_code == 200:
            return response.json()['message']
        elif response.status_code == 500:
            return 'Invalid Invoice ID'
        elif response.status_code == 400:
            return response.json()['errors'][0]
        else:
            return response.text
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None