from telegram import Update
from telegram.ext import CallbackContext
from main import log_command, PRIVATE_GROUP_CHAT_ID
import json
import requests

def add_balance(update: Update, context: CallbackContext) -> None:
    log_command(update, context, 'add_balance')
    
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    admins = config["admins"]

    if update.message.chat_id == PRIVATE_GROUP_CHAT_ID:
        if str(update.message.from_user.id) in admins:
            try:
                parts = update.message.text.split(" ")
                if len(parts) == 3:
                    customer_id = parts[1]
                    amount = parts[2]

                    add_balanceee = add_balancee(customer_id, amount)
                    update.message.reply_text(add_balanceee)
                else:
                    update.message.reply_text("Invalid format: /add_balance <customer_id> <amount>")
            except Exception as e:
                print(f"An error occurred: {e}")

def add_balancee(customer, amount):
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
        API_key = config["api_key"]
        shop = config["shop_id"]

    url = f'https://dev.sellpass.io/self/{shop}/customers/{customer}/balance/add'

    payload = {
        'amount': amount
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
            return 'Invalid Customer ID'
        elif response.status_code == 400:
            return response.json()['errors'][0]
        else:
            return response.text
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None