from telegram import Update, InputFile, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from main import log_command, PRIVATE_GROUP_CHAT_ID
import json
import os
import requests

def invoice(update: Update, context: CallbackContext) -> None:
    log_command(update, context, 'info')
    
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    admins = config["admins"]
    
    if update.message.chat_id == PRIVATE_GROUP_CHAT_ID:
        if str(update.message.from_user.id) in admins:
            try:
                parts = update.message.text.split(" ")
                if len(parts) == 2:
                    invoice_id = parts[1].strip()
                    if not invoice_id:
                        raise ValueError("Invoice ID cannot be empty.")

                    invoice_details, file_paths, status, part_invoice_id = fetch_invoice_details(invoice_id)

                    if invoice_details:
                        keyboard = generate_invoice_keyboard(status, invoice_id, part_invoice_id)
                        reply_markup = InlineKeyboardMarkup(keyboard)

                        update.message.reply_text(
                            text=invoice_details,
                            parse_mode=ParseMode.HTML,
                            reply_markup=reply_markup,
                            reply_to_message_id=update.message.message_id
                        )
                        # File paths are not sent here to prevent immediate upload. They will be handled by callback.
                    else:
                        update.message.reply_text("Unable to fetch invoice details.", reply_to_message_id=update.message.message_id)
                else:
                    update.message.reply_text("Invalid format: /invoice <invoice_id>", reply_to_message_id=update.message.message_id)
            except Exception as e:
                print(f"An error occurred: {e}")
                update.message.reply_text("An unexpected error occurred. Please try again later.")


def fetch_invoice_details(invoice_id: str):
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
            API_key = config["api_key"]
            shop = config["shop_id"]

        url = f"https://dev.sellpass.io/self/{shop}/invoices/{invoice_id}"
        headers = {'Authorization': 'Bearer ' + API_key}

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        data = response.json().get("data", None)
        if not data:
            return 'Invalid Invoice ID', None, None, None

        status_mapping = {0: "New", 3: "Completed", 11: "Expired"}
        gateway_mapping = {0: "Unknown", 7: "Balance", 3: "CashApp", 10: "Hoodpay"}

        status = status_mapping.get(data["status"], "Unknown")
        gateway = gateway_mapping.get(data["gateway"]["gatewayName"], "Unknown")
        email = data["customerInfo"]["customerForShop"]["customer"]["email"]
        ip = data["customerInfo"]["currentIp"]["ip"]
        total_spent = data["customerInfo"]["customerForShop"]["totalSpent"]
        last_time = data["timeline"][-1]["time"] if data["timeline"] else "N/A"

        part_invoice = data["partInvoices"][0]
        product = part_invoice["product"]["title"]
        quantity = part_invoice["quantity"]
        part_invoice_id = part_invoice["id"]
        product_price = data["endPrice"]

        invoice_details = (f'Invoice: <b>{data["id"]}</b>\nPart Invoice ID: <code>{part_invoice_id}</code>\n\n'
                           f'<b>Product</b>\n{quantity}x {product} (${product_price})\n\n'
                           f'<b>Status</b>\n{status}\n\n<b>Order Date</b>\n{last_time}\n\n'
                           f'<b>Gateway</b>\n{gateway}\n\n<b>Email</b>\n<code>{email}</code>\n\n'
                           f'<b>IP</b>\n{ip}\n\n<b>Customer Total Spent</b>\n${total_spent}')



        return invoice_details, None, data["status"], part_invoice_id
    except requests.RequestException as e:
        print(f"Request error: {e}")
        return 'Unable to fetch invoice details.', None, None, None
    except Exception as e:
        print(f"An error occurred while getting details: {e}")
        return 'Unable to fetch invoice details.', None, None, None

def send_invoice_files(update: Update, file_paths: list):
    if not file_paths:
        return
    try:
        for file_path in file_paths:
            with open(file_path, "rb") as file:
                update.message.reply_document(document=InputFile(file), filename=os.path.basename(file_path))
            os.remove(file_path)
    except Exception as e:
        print(f"Error sending files: {e}")

def generate_invoice_keyboard(status: int, invoice_id: str, part_invoice_id: str):
    buttons = []
    if status == 0:  # New
        buttons.append(InlineKeyboardButton("➡️ Process Order", callback_data=f"process_order:{str(invoice_id)}"))
    elif status == 3:  # Completed
        buttons.append(InlineKeyboardButton("🔄 Replace Order", callback_data=f"replace_order:{str(invoice_id)}:{str(part_invoice_id)}"))
        buttons.append(InlineKeyboardButton("📦 Delivered/Replaced Goods", callback_data=f"get_files:{invoice_id}"))
    return [buttons] if buttons else []
