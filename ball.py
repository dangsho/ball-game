import os
from quart import Quart, request
from telegram import Update, Bot, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Application, InlineQueryHandler, MessageHandler, filters, CommandHandler
import sqlite3
import requests
import asyncio
import logging
import jdatetime
import datetime
from pytz import timezone
from hijri_converter import convert

# تنظیم لاگ‌ها
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot_errors.log"),
        logging.StreamHandler()
    ]
)

# تنظیمات توکن و دیتابیس
TOKEN = "8149339547:AAEK7Dkz0VgIWCIT8qJqDvQ88eUuKK5N1x8"
DATABASE = 'game_bot.db'
ADMIN_CHAT_ID = 48232573

if not TOKEN:
    raise ValueError("TOKEN is not set. Please set the token as an environment variable.")

bot = Bot(token=TOKEN)
application = Application.builder().token(TOKEN).build()
flask_app = Quart(__name__)

@flask_app.route('/')
async def home():
    return "سرویس در حال اجرا است 🎉", 200

def get_crypto_price_from_coinmarketcap(crypto_symbol):
    symbol = str(crypto_symbol).upper()
    """دریافت قیمت ارز دیجیتال از CoinMarketCap"""
    try:
        url = f"https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
        headers = {
            "X-CMC_PRO_API_KEY": "8baeefe8-4a9f-4947-8a9d-7f8ea40d91d3",
            "Accept": "application/json",
        }
        params = {"symbol": symbol, "convert": "USD"}
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        price = data["data"][symbol]["quote"]["USD"]["price"]
        return f"{price:,.2f}"
    except requests.RequestException as e:
        logging.error(f"Error fetching data from CoinMarketCap: {e}")
        return None

def get_usdt_to_irr_price(prls):
    """دریافت قیمت تتر به ریال ایران از نوبیتکس"""
    try:
        url = "https://api.nobitex.ir/market/stats"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json().get("stats", {})
            usdt_data = data.get(prls + "-rls", {})
            return int(float(usdt_data.get("latest", 0)))
        return None
    except Exception as e:
        logging.error(f"Error fetching data from Nobitex: {e}")
        return None

async def get_crypto_price_direct(update: Update, context):
    """ارسال قیمت ارز دیجیتال با ارسال مستقیم نام ارز"""
    try:
        # جداسازی متن ورودی
        crypto_name = update.message.text.strip().upper()
        
        # اطمینان از اینکه ورودی یک نام معتبر ارز است
        if " " in crypto_name or crypto_name.startswith(("ADD", "DEL", "LIST")):
            return  # اگر دستور نامعتبر باشد، تابع را ترک کن

        # دریافت قیمت از API
        cmc_price = get_crypto_price_from_coinmarketcap(crypto_name)
        nobitex_price = get_usdt_to_irr_price(crypto_name.lower())

        # پاسخ به کاربر
        if cmc_price or nobitex_price:
            response_message = f"💰 قیمت {crypto_name}:\n"
            if cmc_price:
                response_message += f"- کوین مارکت کپ: ${cmc_price}\n"
            if nobitex_price:
                response_message += f"- نوبیتکس: {nobitex_price:,} ریال\n"
            await update.message.reply_text(response_message)
        else:
            await update.message.reply_text("❌ ارز وارد شده پیدا نشد یا نامعتبر است.")
    except Exception as e:
        logging.error(f"Error in direct price fetch: {e}")
        await update.message.reply_text("⚠️ خطایی رخ داد. لطفاً دوباره تلاش کنید.")

async def inline_query(update: Update, context):
    try:
        # تنظیمات زمان و تاریخ
        tehran_tz = timezone("Asia/Tehran")
        tehran_time = datetime.datetime.now(tehran_tz)
        jalali_date = jdatetime.datetime.fromgregorian(datetime=tehran_time)
        gregorian_date = tehran_time.strftime("%Y-%m-%d")
        islamic_date = convert.Gregorian(tehran_time.year, tehran_time.month, tehran_time.day).to_hijri()
        hijri_date = f"{islamic_date.year}-{islamic_date.month:02d}-{islamic_date.day:02d}"

        # دریافت قیمت‌ها از CoinMarketCap و Nobitex
        bitcoin_price = get_crypto_price_from_coinmarketcap('BTC')
        ethereum_price = get_crypto_price_from_coinmarketcap('ETH')
        tether_price_toman = get_usdt_to_irr_price('usdt')
        xempire_price_toman = get_usdt_to_irr_price('x')
        major_price_toman = get_usdt_to_irr_price('major')

        # ساخت پیام برای ارسال
        message = (
            f'\n@dangsho_bot\n'
            f"\n💰 قیمت ارزهای دیجیتال:\n"
            f"#BTC: ${bitcoin_price}\n"
            f"#ETH: ${ethereum_price}\n"
            f"\nقیمت‌های زیر به #تومان است:\n#Usdt: {tether_price_toman/10}\n"
            f"#Major: {major_price_toman/10}\n"
            f"#X Empire: {xempire_price_toman/10}\n"
            f"\n___________⏰___________:\n\n{tehran_time.strftime('%H:%M:%S')}\n"
            f"📅 تاریخ شمسی:\n{jalali_date.strftime('%Y/%m/%d')}\n"
            f"📅 تاریخ میلادی:\n{gregorian_date}\n"
            f"📅 تاریخ قمری:\n{hijri_date}\n"
        )
        
        game_url = "https://dangsho.github.io/ball-game/"

        # ساختن گزینه‌های اینلاین
        results = [
            InlineQueryResultArticle(
                id="1",
                title="🎮 باز کردن لینک",
                input_message_content=InputTextMessageContent(f"تاریخ را از این لینک باز کنید:\n{game_url}"),
                description="ارسال لینک ⏰"
            ),
            InlineQueryResultArticle(
                id="2",
                title="⏰ ارسال تاریخ و قیمت‌ها به چت", input_message_content=InputTextMessageContent(message),
                description="ارسال تاریخ و قیمت‌ ارزها به چت"
            )
        ]
        await update.inline_query.answer(results, cache_time=10)
    except Exception as e:
        logging.error(f"Error in inline query handler: {e}")


# مدیریت لیست ارزها برای کاربران
def setup_database():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    # جدول لیست ارزهای کاربران
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_cryptos (
            user_id INTEGER,
            crypto_symbol TEXT,
            PRIMARY KEY (user_id, crypto_symbol)
        )
    ''')
    # جدول سایر داده‌ها
    c.execute('''CREATE TABLE IF NOT EXISTS game_sessions
                 (unique_id TEXT, user_id INTEGER, game_short_name TEXT, inline_message_id TEXT)''')
    conn.commit()
    conn.close()

# اضافه کردن ارز به لیست کاربر
async def add_crypto(update: Update, context):
    try:
        user_id = update.effective_user.id
        message = update.message.text.split()
        if len(message) < 2:
            await update.message.reply_text("❗️ دستور صحیح: add <نام_ارز>")
            return
        crypto_symbol = message[1].upper()
        
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO user_cryptos (user_id, crypto_symbol) VALUES (?, ?)", (user_id, crypto_symbol))
        conn.commit()
        conn.close()
        
        await update.message.reply_text(f"✅ ارز {crypto_symbol} به لیست شما اضافه شد.")
    except Exception as e:
        logging.error(f"Error in add_crypto: {e}")
        await update.message.reply_text("⚠️ خطایی رخ داد. لطفاً دوباره تلاش کنید.")

# حذف ارز از لیست کاربر
async def del_crypto(update: Update, context):
    try:
        user_id = update.effective_user.id
        message = update.message.text.split()
        if len(message) < 2:
            await update.message.reply_text("❗️ دستور صحیح: del <نام_ارز>")
            return
        crypto_symbol = message[1].upper()
        
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("DELETE FROM user_cryptos WHERE user_id = ? AND crypto_symbol = ?", (user_id, crypto_symbol))
        conn.commit()
        conn.close()
        
        await update.message.reply_text(f"✅ ارز {crypto_symbol} از لیست شما حذف شد.")
    except Exception as e:
        logging.error(f"Error in del_crypto: {e}")
        await update.message.reply_text("⚠️ خطایی رخ داد. لطفاً دوباره تلاش کنید.")

# نمایش لیست ارزهای کاربر به همراه قیمت
async def list_cryptos(update: Update, context):
    try:
        user_id = update.effective_user.id
        
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("SELECT crypto_symbol FROM user_cryptos WHERE user_id = ?", (user_id,))
        cryptos = [row[0] for row in c.fetchall()]
        conn.close()
        
        if not cryptos:
            await update.message.reply_text("ℹ️ لیست شما خالی است. از دستور add برای اضافه کردن ارز استفاده کنید.")
            return
        
        response = "💰 لیست ارزهای شما:\n"
        for crypto in cryptos:
            price = get_crypto_price_from_coinmarketcap(crypto)
            response += f"- {crypto}: ${price if price else 'نامشخص'}\n"
        
        await update.message.reply_text(response)
    except Exception as e:
        logging.error(f"Error in list_cryptos: {e}")
        await update.message.reply_text("⚠️ خطایی رخ داد. لطفاً دوباره تلاش کنید.")

     
# تابع برای تنظیم Webhook
async def set_webhook():
    public_url = os.getenv("RENDER_EXTERNAL_URL")
    if not public_url:
        raise ValueError("RENDER_EXTERNAL_URL is not set. This should be provided by Render.")
    webhook_url = f"{public_url}/webhook"
    set_webhook_response = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/setWebhook",
        json={"url": webhook_url}
    )
    if set_webhook_response.status_code != 200:
        logging.error(f"Failed to set webhook: {set_webhook_response.text}")
        raise RuntimeError(f"Failed to set webhook: {set_webhook_response.text}")
    else:
        logging.info(f"Webhook set to: {webhook_url}")

@flask_app.route('/webhook', methods=['POST'])
        
async def webhook_update():
    if request.method == "POST":
        try:
            data = await request.get_json()
            update = Update.de_json(data, bot)
            await application.update_queue.put(update)
            return 'ok', 200
        except Exception as e:
            logging.error(f"Error processing webhook: {e}")
            return 'Bad Request', 400

# تابع اصلی برای راه‌اندازی برنامه
async def main():
    setup_database()  # راه‌اندازی دیتابیس در ابتدای برنامه

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, get_crypto_price_direct))
    application.add_handler(CommandHandler("add", add_crypto))
    application.add_handler(CommandHandler("del", del_crypto))
    application.add_handler(CommandHandler("list", list_cryptos))
    
    await set_webhook()
    await application.initialize()
    asyncio.create_task(application.start())

    port = int(os.getenv('PORT', 5000))
    await flask_app.run_task(host="0.0.0.0", port=port)

if __name__ == '__main__':
    asyncio.run(main())