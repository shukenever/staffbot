from telegram import Update
from telegram.ext import CallbackContext
from main import log_command, PRIVATE_GROUP_CHAT_ID
import json
import requests

def invoices(update: Update, context: CallbackContext) -> None:
    log_command(update, context, 'invoices')
    
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    admins = config["admins"]

    if update.message.chat_id == PRIVATE_GROUP_CHAT_ID:
        if str(update.message.from_user.id) in admins:
            try:
                parts = update.message.text.split(" ")
                if len(parts) == 2:
                    email = str(parts[1])
                    
                    invoices_list = invoicess(email)

                    if '@' in email:
                        if invoices_list:
                            response_text = f"Invoices: {email}\n\n"
                            for invoice in invoices_list:
                                response_text += f'{invoice}\n'
                            
                            update.message.reply_text(response_text, parse_mode='Markdown', reply_to_message_id=update.message.message_id)
                        else:
                            update.message.reply_text("No invoices found for this email.", reply_to_message_id=update.message.message_id)
                    else:
                        update.message.reply_text('Invalid email', reply_to_message_id=update.message.message_id)
                else:
                    update.message.reply_text("Invalid format: /invoices <email>", reply_to_message_id=update.message.message_id)
            except Exception as e:
                print(f"An error occurred: {e}")

def invoicess(email):
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
        API_key = config["api_key"]
        shop = config["shop_id"]
    
    url = f"https://dev.sellpass.io/self/{shop}/invoices/?searchString={email}"
    headers = {
        'Authorization': 'Bearer '+API_key
    }

    status_dict = {
        0: "New",
        3: "Completed",
        11: "Expired"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        response_data = response.json()
        
        if 'data' not in response_data:
            return 'No Customer found.'
        
        messages = []
        for order in response_data['data']:
            invoice_id = order['id']
            product_info = order['partInvoices'][0]
            product_quantity = product_info['quantity']
            product_title = product_info['product']['title']
            product_price = product_info['rawPrice']
            order_status = order['status']
            last_timeline_entry = order["timeline"][-1] if order["timeline"] else {}
            last_time = last_timeline_entry.get("time", "N/A")

            status_description = status_dict.get(order_status, "Unknown")
            message = f"*{invoice_id}*\n"
            message += f"{product_quantity}x {product_title} (${product_price}, {status_description}, {last_time})\n"
            messages.append(message)

        return messages
            
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while getting details: {e}")
        return None