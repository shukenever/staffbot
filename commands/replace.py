from telegram import Update
from telegram.ext import CallbackContext
from main import log_command, PRIVATE_GROUP_CHAT_ID
import json
import requests

def replace(update: Update, context: CallbackContext) -> None:
    log_command(update, context, 'replace')
    
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    admins = config["admins"]

    if update.message.chat_id == PRIVATE_GROUP_CHAT_ID:
        if str(update.message.from_user.id) in admins:
            try:
                parts = update.message.text.split(" ")
                if len(parts) == 4:
                    invoice_id = str(parts[1])
                    partinvoice_id = int(parts[2])
                    quantity = int(parts[3])
                    
                    replaceee = replacee(invoice_id, partinvoice_id, quantity)
                    update.message.reply_text(replaceee, reply_to_message_id=update.message.message_id)
                else:
                    update.message.reply_text("Invalid format: /replace <invoice_id> <partinvoiceid> <quantity>", reply_to_message_id=update.message.message_id)
            except Exception as e:
                print(f"An error occurred: {e}")

def replacee(invoice_id, partinvoice_id, quanitty):
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
        API_key = config["api_key"]
        shop = config["shop_id"]

    url = f'https://dev.sellpass.io/self/{shop}/invoices/{invoice_id}/replacement'

    payload = {
        "partInvoiceId": partinvoice_id,
        "quantity": quanitty
    }

    json_payload = json.dumps(payload)

    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer '+API_key
        }

    try:
        response = requests.post(url, headers=headers, data=json_payload)
        
        if response.status_code == 200:
            return response.json()['message']
        elif response.status_code == 500:
            return 'Invalid Invoice/Part Invoice ID.'
        elif response.status_code == 400:
            return response.json()['errors'][0]
        else:
            return response.text
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None