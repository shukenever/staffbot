import logging
import commands
import json
import os
import requests
from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler

AUTHORIZED_USER_IDS = [5211092406]
BOT_TOKEN = '7035714116:AAE7qOpZhJo7n8KXI091U2dvPehCClme7cM'
PRIVATE_GROUP_CHAT_ID = -1002122178431

def get_command_logger(command_name: str) -> logging.Logger:
    logger = logging.getLogger(command_name)
    if not logger.hasHandlers():
        handler = logging.FileHandler(f'log/{command_name}.log', encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

def log_message(update: Update, context: CallbackContext) -> None:
    print(update.message)
    user = update.message.from_user
    message_logger = get_command_logger('messages')
    message_logger.info("Message from %s (%s) (@%s): %s", user.first_name, user.id, user.username, update.message.text)

def log_command(update: Update, context: CallbackContext, command_name: str) -> None:
    user = update.message.from_user
    command_logger = get_command_logger(command_name)
    command_logger.info("Command from %s (%s) (@%s): %s", user.first_name, user.id, user.username, update.message.text)

def callback_query_handler(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    data = query.data.split(':')
    
    if data[0] == "add_balance":
        customer_id = data[1]
        query.edit_message_text(f"@{query.from_user.username}, Select an amount to add:", reply_markup=get_amount_keyboard(customer_id))
    elif data[0] == "amount":
        amount = data[1]
        if amount == "other":
            customer_id = data[2]
            query.edit_message_text(f"@{query.from_user.username}, Please enter the amount you want to add:")
            context.user_data['awaiting_amount'] = True
            context.user_data['customer_id'] = customer_id
        else:
            customer_id = data[2]
            msg, adding_balance = add_balance_to_user(customer_id, float(amount))
            if adding_balance == 200:
                query.edit_message_text(f"@{query.from_user.username} Added ${amount} to customer ID {customer_id}.")
            elif adding_balance == 500:
                update.message.reply_text("An error occurred: Invalid Customer ID.")
            elif adding_balance == 400:
                update.message.reply_text("An error occurred: "+msg)
            else:
                update.message.reply_text("An error occurred. Please try again.")
    elif data[0] == "replace_order":
        invoice_id = data[1]
        part_invoice_id = data[2]

        query.edit_message_text(f"@{query.from_user.username} Please enter the amount of replacements:")
        context.user_data['awaiting_replace_amount'] = True
        context.user_data['invoice_id'] = invoice_id
        context.user_data['part_invoice_id'] = part_invoice_id
    elif data[0] == "get_files":
        invoice_id = data[1]
        _, file_paths, _, _ = fetch_invoice_details(invoice_id)
        send_invoice_files(query, file_paths)
    elif data[0] == "process_order":
        invoice_id = data[1]
        errormsg, status = processs(invoice_id)

        if status == 200:
            query.edit_message_text(f'@{query.from_user.username}, {errormsg}', parse_mode=ParseMode.HTML)
        elif status == 400:
            query.edit_message_text(f"@{query.from_user.username}, An error occurred: {errormsg}")
        elif status == 500:
            query.edit_message_text(f"@{query.from_user.username}, An error occurred: {errormsg}")
        else:
            query.edit_message_text(f"@{query.from_user.username}, An error occurred. Please try again.")
    elif data[0] == "cancel":
        query.edit_message_text("Cancelled.")

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
            return f'Successfully Processed invoice ID: <code><b>{invoice_id}</b></code>', response.status_code
        elif response.status_code == 500:
            return 'Invalid Invoice ID', response.status_code
        elif response.status_code == 400:
            return response.json()['errors'][0], response.status_code
        else:
            return response.text
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None
    
def send_invoice_files(query, file_paths: list):
    if not file_paths:
        query.edit_message_text(text="No delivered or replaced goods files available.")
        return
    try:
        for file_path in file_paths:
            with open(file_path, "rb") as file:
                query.message.reply_document(document=InputFile(file), filename=os.path.basename(file_path))
            os.remove(file_path)
    except Exception as e:
        print(f"Error sending files: {e}")

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

        file_paths = []
        if data["status"] == 3:  #Completed
            if part_invoice["deliveredGoods"]:
                delivered_goods = "\n".join(part_invoice["deliveredGoods"])
                delivered_file_path = f"delivered_goods_{invoice_id}.txt"

                with open(delivered_file_path, "w", encoding="utf-8") as file:
                    file.write(delivered_goods)

                file_paths.append(delivered_file_path)

            if part_invoice.get("replacements"):
                for replacement in part_invoice["replacements"]:
                    if replacement["deliveredGoods"]:
                        replacement_goods = "\n".join(replacement["deliveredGoods"])
                        replacement_file_path = f"replacement_goods_{invoice_id}_{replacement['id']}.txt"

                        with open(replacement_file_path, "w", encoding="utf-8") as file:
                            file.write(replacement_goods)

                        file_paths.append(replacement_file_path)

        return invoice_details, file_paths, data["status"], part_invoice_id
    except requests.RequestException as e:
        print(f"Request error: {e}")
        return 'Unable to fetch invoice details.', None, None, None
    except Exception as e:
        print(f"An error occurred while getting details: {e}")
        return 'Unable to fetch invoice details.', None, None, None


def add_balance_to_user(customer_id, amount):
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
        API_key = config["api_key"]
        shop = config["shop_id"]

    url = f'https://dev.sellpass.io/self/{shop}/customers/{customer_id}/balance/add'

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
            return f'Added ${amount} to customer ID {customer_id}.', response.status_code
        elif response.status_code == 500:
            return (f"An error occurred: Invalid Customer ID"), response.status_code
        elif response.status_code == 400:
            return response.json()['errors'][0], response.status_code
        else:
            print(f"An error occurred: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None

def get_amount_keyboard(customer_id):
    amounts = [5, 10, 15, 20]
    keyboard = [[InlineKeyboardButton(f"💵 ${amt}", callback_data=f"amount:{amt}:{customer_id}") for amt in amounts],
                [InlineKeyboardButton("Other", callback_data=f"amount:other:{customer_id}")], [InlineKeyboardButton("❌ Cancel ❌", callback_data="cancel")]]
    return InlineKeyboardMarkup(keyboard)

def handle_message(update: Update, context: CallbackContext) -> None:
    if context.user_data.get('awaiting_amount'):
        try:
            amount = float(update.message.text)
            customer_id = context.user_data.get('customer_id')
            if customer_id:
                msg, response_code = add_balance_to_user(customer_id, float(amount))
                if response_code == 200:
                    update.message.reply_text(msg)
                elif response_code == 500:
                    update.message.reply_text("An error occurred: Invalid Customer ID.")
                elif response_code == 400:
                    update.message.reply_text("An error occurred: "+msg)
                else:
                    update.message.reply_text("An error occurred. Please try again.")
                context.user_data['awaiting_amount'] = False
            else:
                update.message.reply_text("Error: Customer ID not found.")
        except ValueError:
            update.message.reply_text("Please enter a valid number.")
    elif context.user_data.get('awaiting_replace_amount'):
        try:
            replace_amount = int(update.message.text)
            part_invoice_id = context.user_data.get('part_invoice_id')
            invoice_id = context.user_data.get('invoice_id')
            if part_invoice_id and invoice_id:
                errormsg, replace_order = replace_orderr(invoice_id, part_invoice_id, replace_amount)

                if replace_order == 200:
                    update.message.reply_text(f"Replaced x{replace_amount} to Invoice ID {invoice_id}.")
                elif replace_order == 500:
                    update.message.reply_text(f"Invalid Invoice/Part Invoice ID.")
                elif replace_order == 400:
                    update.message.reply_text(f"An Error Occured: "+errormsg[0])
                else:
                    update.message.reply_text("An error occurred. Please try again.")
                context.user_data['awaiting_replace_amount'] = False
            else:
                update.message.reply_text("Error: Customer ID not found.")
        except ValueError:
            update.message.reply_text("Please enter a valid replacement amount.")

def replace_orderr(invoice_id, partinvoice_id, quanitty):
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
            return None, response.status_code
        elif response.status_code == 500:
            return 'Invalid Invoice/Part Invoice ID.', response.status_code
        elif response.status_code == 400:
            return response.json()['errors'], response.status_code
        else:
            print(response.text)
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None, None

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('add_admin', commands.add_admin))
    dp.add_handler(CommandHandler('add_balance', commands.add_balance))
    dp.add_handler(CommandHandler('admins', commands.admins))
    dp.add_handler(CommandHandler('blacklist', commands.blacklist))
    dp.add_handler(CommandHandler('help', commands.help))
    dp.add_handler(CommandHandler('info', commands.info))
    dp.add_handler(CommandHandler('invoice', commands.invoice))
    dp.add_handler(CommandHandler('invoices', commands.invoices))
    dp.add_handler(CommandHandler('process', commands.process))
    dp.add_handler(CommandHandler('remove_admin', commands.remove_admin))
    dp.add_handler(CommandHandler('remove_balance', commands.remove_balance))
    dp.add_handler(CommandHandler('replace', commands.replace))
    dp.add_handler(CommandHandler('resend', commands.resend))
    dp.add_handler(CommandHandler('start', commands.start))
    dp.add_handler(CallbackQueryHandler(callback_query_handler))
    
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dp.add_handler(MessageHandler(Filters.text & (~Filters.command), log_message))

    updater.start_polling()
    print('Bot is now Online!')
    updater.idle()

if __name__ == '__main__':
    main()
