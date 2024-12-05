import os
from quart import Quart, request
from telegram import Update, Bot, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Application, CommandHandler, InlineQueryHandler, MessageHandler, filters
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
ADMIN_CHAT_ID = 48232573  # آیدی چت مدیر را اینجا وارد کنید

if not TOKEN:
    raise ValueError("TOKEN is not set. Please set the token as an environment variable.")

bot = Bot(token=TOKEN)
application = Application.builder().token(TOKEN).build()
flask_app = Quart(__name__)

@flask_app.route('/')
async def home():
    return "سرویس در حال اجرا است 🎉", 200

async def notify_admin(user_id: int, username: str = None):
    """ارسال پیام اطلاع‌رسانی به مدیر"""
    try:
        message = f"🔔 کاربر جدید از ربات استفاده کرد:\n\n👤 آیدی کاربر: {user_id}"
        if username:
            message += f"\n📛 نام کاربری: @{username}"
        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=message)
    except Exception as e:
        logging.error(f"Error notifying admin: {e}")

async def start(update: Update, context):
    try:
        game_url = "https://dangsho.github.io/ball-game/"
        await update.message.reply_text(f" برای دیدن تاریخ کلیک کنید:\n{game_url}")

        # ارسال اطلاع‌رسانی به مدیر
        await notify_admin(
            user_id=update.message.from_user.id,
            username=update.message.from_user.username
        )
    except Exception as e:
        logging.error(f"Error in /start handler: {e}")
        await update.message.reply_text("متأسفیم، مشکلی پیش آمده است.")

def get_crypto_price_from_coinmarketcap(crypto_symbol):
    """دریافت قیمت ارز دیجیتال از CoinMarketCap"""
    try:
        url = f"https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
        headers = {
            "X-CMC_PRO_API_KEY": "8baeefe8-4a9f-4947-8a9d-7f8ea40d91d3",
            "Accept": "application/json",
        }
        params = {"symbol": crypto_symbol, "convert": "USD"}
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        price = data["data"][crypto_symbol]["quote"]["USD"]["price"]
        return f"{price:,.2f}"
    except requests.RequestException as e:
        logging.error(f"Error fetching data from CoinMarketCap: {e}")
        return "خطا در دریافت اطلاعات"

def get_usdt_to_irr_price():
    """دریافت قیمت تتر به ریال ایران از نوبیتکس"""
    try:
        # ارسال درخواست به API نوبیتکس
        url = "https://api.nobitex.ir/market/stats"
        response = requests.get(url)
        
        # بررسی موفقیت‌آمیز بودن درخواست
        if response.status_code == 200:
            data = response.json().get("stats", {})
            
            # استخراج قیمت تتر به ریال (USDT-IRR)
            usdt_data = data.get("usdt-rls", {})
            latest_price = usdt_data.get("latest")
            if latest_price:
                return f"{int(float(latest_price)):,} ریال"
            else:
                return "قیمت تتر به ریال موجود نیست."
        
        elif response.status_code == 429:
            logging.error("Rate limit exceeded for Nobitex API. Try again later.")
            return "محدودیت درخواست‌ها"
        else:
            logging.error(f"Failed to fetch data from Nobitex: {response.status_code} - {response.text}")
            return "خطا در دریافت داده‌ها"
    except Exception as e:
        logging.error(f"Error fetching data from Nobitex: {e}")
        return "خطای سیستم"

# تعریف لیست ارزهای پشتیبانی‌شده
AVAILABLE_CRYPTO_SYMBOLS = ['BTC', 'ETH', 'USDT']  # می‌توانید ارزهای بیشتری اضافه کنید.

async def handle_crypto_price(update: Update, context):
    """هندلر برای دریافت پیام کاربر و ارسال قیمت رمز ارز در صورت معتبر بودن"""
    try:
        crypto_name = update.message.text.strip().upper()  # دریافت نام رمز ارز و تبدیل به حروف بزرگ

        # بررسی معتبر بودن نماد رمز ارز
        if crypto_name not in AVAILABLE_CRYPTO_SYMBOLS:
            logging.debug(f"Invalid or unsupported crypto name: {crypto_name}")
            return  # اگر نماد معتبر نبود، هیچ پاسخی ارسال نشود

        # دریافت قیمت از منابع
        cmc_price = get_crypto_price_from_coinmarketcap(crypto_name)
        nobitex_price = get_usdt_to_irr_price()

        # بررسی صحت اطلاعات و ایجاد پیام پاسخ
        if cmc_price == "خطا در دریافت اطلاعات" and "خطا" in nobitex_price:
            logging.debug(f"Failed to fetch prices for: {crypto_name}")
            return  # در صورت بروز خطا نیز پاسخی ارسال نمی‌شود

        response_message = (
            f"💰 قیمت رمز ارز '{crypto_name}':\n"
            f"- کوین مارکت کپ: ${cmc_price}\n"
            f"- نوبیتکس: {nobitex_price}\n"
        )

        await update.message.reply_text(response_message)  # ارسال پاسخ به کاربر

    except Exception as e:
        logging.error(f"Error in handle_crypto_price: {e}")

async def inline_query(update: Update, context):
    try:
        # مقداردهی اولیه results برای جلوگیری از خطای UnboundLocalError
        results = []

        # زمان به وقت تهران
        tehran_tz = timezone("Asia/Tehran")
        tehran_time = datetime.datetime.now(tehran_tz)

        # تاریخ شمسی
        jalali_date = jdatetime.datetime.fromgregorian(datetime=tehran_time)

        # تاریخ میلادی
        gregorian_date = tehran_time.strftime("%Y-%m-%d")

        # تاریخ قمری
        islamic_date = convert.Gregorian(tehran_time.year, tehran_time.month, tehran_time.day).to_hijri()
        hijri_date = f"{islamic_date.year}-{islamic_date.month:02d}-{islamic_date.day:02d}"

        # دریافت قیمت ارزهای دیجیتال
        bitcoin_price = get_crypto_price_from_coinmarketcap('BTC')
        ethereum_price = get_crypto_price_from_coinmarketcap('ETH')
        tether_price_toman = get_usdt_to_irr_price()

        # ساختن متن پیام تاریخ و قیمت ثابت
        message = (
            f'@dangsho_bot\n\n'
            
            f"\n💰 قیمت ارزهای دیجیتال:\n"
            f"₿ بیت‌کوین: ${bitcoin_price}\n"
            f" اتریوم: ${ethereum_price}\n"
            f"💵 تتر: {tether_price_toman}\n"
            
            f"⏰:\n{tehran_time.strftime('%H:%M:%S')}\n"
            f"📅 تاریخ شمسی:\n{jalali_date.strftime('%Y/%m/%d')}\n"
            f"📅 تاریخ میلادی:\n{gregorian_date}\n"
            f"📅 تاریخ قمری:\n{hijri_date}\n"
        )

        # لینک بازی
        game_url = "https://dangsho.github.io/ball-game/"

        # ساختن نتایج اینلاین
        results = [
            InlineQueryResultArticle(
                id="1",
                title="🎮 باز کردن لینک",
                input_message_content=InputTextMessageContent(f"تاریخ را از این لینک باز کنید:\n{game_url}"),
                description="ارسال لینک ⏰"
            ),
            InlineQueryResultArticle(
                id="2",
                title="⏰ ارسال تاریخ و قیمت‌ها به چت",
                input_message_content=InputTextMessageContent(message),
                description="ارسال تاریخ و قیمت‌ ارزها به چت"
            ),
        ]
        await update.inline_query.answer(results, cache_time=0)

    except Exception as e:
        logging.error(f"Error in inline query handler: {e}")

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

async def main():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS game_sessions
                 (unique_id TEXT, user_id INTEGER, game_short_name TEXT, inline_message_id TEXT)''')
    conn.commit()
    conn.close()

    await bot.initialize()
    
    # افزودن هندلرهای مختلف
    application.add_handler(CommandHandler("start", start))
    application.add_handler(InlineQueryHandler(inline_query))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_crypto_price))  # هندلر پیام متنی

    await set_webhook()

    await application.initialize()
    asyncio.create_task(application.start())

    port = int(os.getenv('PORT', 5000))
    await flask_app.run_task(host="0.0.0.0", port=port)

if __name__ == '__main__':
    asyncio.run(main())