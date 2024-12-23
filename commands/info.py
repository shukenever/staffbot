from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import CallbackContext
from main import log_command, PRIVATE_GROUP_CHAT_ID
import json
import requests

def info(update: Update, context: CallbackContext) -> None:
    log_command(update, context, 'info')
    
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    admins = config["admins"]
    
    if update.message.chat_id == PRIVATE_GROUP_CHAT_ID:
        if str(update.message.from_user.id) in admins:
            try:
                parts = update.message.text.split(" ")
                if len(parts) == 2:
                    email = str(parts[1])

                    if '@' in email:
                        infooo, customerID = infoo(email)
                        if customerID:
                            keyboard = [[InlineKeyboardButton("💳 Add Balance", callback_data=f'add_balance:{str(customerID)}')]]
                            reply_markup = InlineKeyboardMarkup(keyboard)
                            context.bot.send_message(chat_id=update.effective_chat.id, text=infooo, reply_markup=reply_markup)
                        else:
                            context.bot.send_message(chat_id=update.effective_chat.id, text=infooo)
                    else:
                        update.message.reply_text('Invalid email.', reply_to_message_id=update.message.message_id)
                else:
                    update.message.reply_text("Please provide an email to search.")
            except Exception as e:
                print(f"An error occurred: {e}")

def infoo(email):
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
        API_key = config["api_key"]
        shop = config["shop_id"]
    url = f"https://dev.sellpass.io/self/{shop}/customers?searchString={email}"
    headers = {
        'Authorization': 'Bearer ' + API_key
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        response_data = response.json()
        if not response_data['data']:
            return f'No Customer found with email {email}', None
        else:
            entry = response_data['data'][0]
            total_spent = entry['totalSpent']
            total_purchases = entry['totalPurchases']
            is_blocked = entry['isBlocked']
            customer_email = entry['customer']['email']
            customer_id = entry['id']
            
            if 'customerForShopAccount' in entry:
                account_info = entry['customerForShopAccount']
                real_balance = next((balance['realBalance'] for balance in account_info['balances'] if balance['currency'] == 'USD'), 0)
                manual_balance = next((balance['manualBalance'] for balance in account_info['balances'] if balance['currency'] == 'USD'), 0)
            else:
                real_balance = 0
                manual_balance = 0
            
            return f'Customer ID: {customer_id}\nCustomer Email: {customer_email}\nTotal Spent: {total_spent}\nTotal Purchases: {total_purchases}\nBlocked: {is_blocked}\nReal Balance: ${real_balance}\nManual Balance: ${manual_balance}', customer_id
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while getting details: {e}")
        return None, None
