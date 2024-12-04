import os
from quart import Quart, request
from telegram import Update, Bot, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Application, CommandHandler, InlineQueryHandler
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
TOKEN = os.getenv("TOKEN", "8149339547:AAEK7Dkz0VgIWCIT8qJqDvQ88eUuKK5N1x8")
DATABASE = 'game_bot.db'
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "48232573"))

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
        await update.message.reply_text(f"برای دیدن تاریخ کلیک کنید:\n{game_url}")

        # ارسال اطلاع‌رسانی به مدیر
        await notify_admin(
            user_id=update.message.from_user.id,
            username=update.message.from_user.username
        )
    except Exception as e:
        logging.error(f"Error in /start handler: {e}")
        await update.message.reply_text("متأسفیم، مشکلی پیش آمده است.")

def get_crypto_price_from_coingecko(crypto_name):
    """دریافت قیمت ارز دیجیتال از کوین‌گکو"""
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={crypto_name}&vs_currencies=usd"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data.get(crypto_name, {}).get("usd", "ناموجود")
        elif response.status_code == 429:
            logging.error("Rate limit exceeded for CoinGecko API. Try again later.")
            return "بیش از حد مجاز"
        else:
            logging.error(f"Failed to fetch price from CoinGecko: {response.status_code} - {response.text}")
            return "ناموجود"
    except Exception as e:
        logging.error(f"Error fetching price from CoinGecko: {e}")
        return "خطا"

def get_crypto_price_from_nobitex(crypto_name):
    """دریافت قیمت ارز دیجیتال از نوبیتکس"""
    try:
        url = "https://api.nobitex.ir/market/stats"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json().get("stats", {})
            market_key = f"{crypto_name}-irt"
            return data.get(market_key, {}).get("last", "ناموجود")
        elif response.status_code == 429:
            logging.error("Rate limit exceeded for Nobitex API. Try again later.")
            return "بیش از حد مجاز"
        else:
            logging.error(f"Failed to fetch price from Nobitex: {response.status_code} - {response.text}")
            return "ناموجود"
    except Exception as e:
        logging.error(f"Error fetching price from Nobitex: {e}")
        return "خطا"

async def inline_query(update: Update, context):
    try:
        results = []
        # زمان به وقت تهران
        tehran_tz = timezone("Asia/Tehran")
        tehran_time = datetime.datetime.now(tehran_tz)

        # تاریخ شمسی، میلادی، و قمری
        jalali_date = jdatetime.datetime.fromgregorian(datetime=tehran_time)
        gregorian_date = tehran_time.strftime("%Y-%m-%d")
        islamic_date = convert.Gregorian(tehran_time.year, tehran_time.month, tehran_time.day).to_hijri()
        hijri_date = f"{islamic_date.year}-{islamic_date.month:02d}-{islamic_date.day:02d}"

        # دریافت قیمت ارزهای دیجیتال
        bitcoin_price = get_crypto_price_from_coingecko('bitcoin')
        ethereum_price = get_crypto_price_from_coingecko('ethereum')
        tether_price_toman = get_crypto_price_from_nobitex('usdt')

        # ساختن متن پیام
        message = (
            f'⏰ تهران:\n{tehran_time.strftime("%H:%M:%S")}\n\n'
            f"📅 تاریخ شمسی: {jalali_date.strftime('%Y/%m/%d')}\n"
            f"📅 تاریخ میلادی: {gregorian_date}\n"
            f"📅 تاریخ قمری: {hijri_date}\n\n"
            f"💰 قیمت ارزها:\n"
            f"₿ بیت‌کوین: ${bitcoin_price}\n"
            f"Ξ اتریوم: ${ethereum_price}\n"
            f"💵 تتر: {tether_price_toman:,} تومان"
        )

        # ساخت نتایج اینلاین
        results.append(InlineQueryResultArticle(
            id="info",
            title="تاریخ و قیمت‌ها",
            input_message_content=InputTextMessageContent(message)
        ))

        # ارسال نتایج
        await update.inline_query.answer(results, cache_time=0)

    except Exception as e:
        logging.error(f"Error in inline query: {e}")
        await update.inline_query.answer([], cache_time=0)

async def main():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS game_sessions
                 (unique_id TEXT, user_id INTEGER, game_short_name TEXT, inline_message_id TEXT)''')
    conn.commit()
    conn.close()

    await bot.initialize()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(InlineQueryHandler(inline_query))

    await application.initialize()
    asyncio.create_task(application.start())

    port = int(os.getenv('PORT', 5000))
    await flask_app.run_task(host="0.0.0.0", port=port)

if __name__ == "__main__":
    asyncio.run(main())
