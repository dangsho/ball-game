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
TOKEN = "8149339547:AAEK7Dkz0VgIWCIT8qJqDvQ88eUuKK5N1x8"
DATABASE = 'game_bot.db'
ADMIN_CHAT_ID = 48232573  # آیدی چت مدیر را اینجا وارد کنید

if not TOKEN:
    raise ValueError("TOKEN is not set. Please set the token as an environment variable.")

bot = Bot(token=TOKEN)
application = Application.builder().token(TOKEN).build()
flask_app = Quart(__name__)

# تابع برای دریافت قیمت ارزهای دیجیتال
def get_crypto_prices():
    try:
        # دریافت قیمت ارزهای دیجیتال به دلار از CoinGecko
        response = requests.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,notecoin&vs_currencies=usd"
        )
        if response.status_code == 200:
            data = response.json()
            bitcoin_price = data.get("bitcoin", {}).get("usd", "ناموجود")
            ethereum_price = data.get("ethereum", {}).get("usd", "ناموجود")
            notecoin_price = data.get("notecoin", {}).get("usd", "ناموجود")
        else:
            logging.error(f"Failed to fetch crypto prices: {response.text}")
            bitcoin_price, ethereum_price, notecoin_price = "ناموجود", "ناموجود", "ناموجود"
    except Exception as e:
        logging.error(f"Error fetching crypto prices: {e}")
        bitcoin_price, ethereum_price, notecoin_price = "ناموجود", "ناموجود", "ناموجود"

    # دریافت قیمت تتر به تومان از نوبیتکس
    try:
        tether_response = requests.get("https://api.nobitex.ir/market/stats")
        if tether_response.status_code == 200:
            tether_data = tether_response.json()
            tether_price_toman = tether_data["stats"]["usdt-irt"]["last"]
        else:
            logging.error(f"Failed to fetch Tether price from Nobitex: {tether_response.text}")
            tether_price_toman = "ناموجود"
    except Exception as e:
        logging.error(f"Error fetching Tether price from Nobitex: {e}")
        tether_price_toman = "ناموجود"

    return bitcoin_price, ethereum_price, notecoin_price, tether_price_toman


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

async def inline_query(update: Update, context):
    try:
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
        bitcoin_price, ethereum_price, notecoin_price, tether_price_toman = get_crypto_prices()

        # ساختن متن پیام
        message = (
            f'@dangsho_bot\n\n'
            f"⏰ تهران:\n{tehran_time.strftime('%H:%M:%S')}\n\n"
            f"📅 تاریخ شمسی:\n{jalali_date.strftime('%Y/%m/%d')}\n\n"
            f"📅 تاریخ میلادی:\n{gregorian_date}\n\n"
            f"📅 تاریخ قمری:\n{hijri_date}\n\n"
            f"💰 قیمت ارزهای دیجیتال:\n"
            f"₿ بیت‌کوین: ${bitcoin_price}\n"
            f"Ξ اتریوم: ${ethereum_price}\n"
            f"💲 نات‌کوین: ${notecoin_price}\n"
            f"💵 تتر: {tether_price_toman:,} تومان"
        )

        logging.debug(f"Generated message: {message}")

        # لینک بازی
        game_url = "https://dangsho.github.io/ball-game/"

        # ساختن نتایج اینلاین
        results = [
            InlineQueryResultArticle(
                id="1",
                title="🎮 باز کردن لینک ",
                input_message_content=InputTextMessageContent(f"تاریخ  را از این لینک باز کنید:\n{game_url}"),
                description=" ارسال لینک  ⏰"
            ),
            InlineQueryResultArticle(
                id="2",
                title="⏰ ارسال تاریخ و قیمت‌ها به چت",
                input_message_content=InputTextMessageContent(message),
                description="ارسال تاریخ و قیمت‌ها به چت"
            )
        ]

        # ارسال پاسخ به اینلاین کوئری با غیرفعال کردن کش
        await update.inline_query.answer(results, cache_time=0)

        # ارسال اطلاع‌رسانی به مدیر
        await notify_admin(
            user_id=update.inline_query.from_user.id,
            username=update.inline_query.from_user.username
        )
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

async def check_webhook():
    try:
        # درخواست اطلاعات وبهوک
        response = requests.get(f"https://api.telegram.org/bot{TOKEN}/getWebhookInfo")
        response_data = response.json()

        if response.status_code == 200 and response_data.get("ok"):
            logging.info("Webhook is set correctly: %s", response_data)
        else:
            logging.error("Failed to retrieve webhook info. Response: %s", response_data)
            raise ValueError(f"Webhook check failed: {response_data.get('description')}")
    except Exception as e:
        logging.error(f"Error while checking webhook: {e}")

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

    await set_webhook()
    await check_webhook()

    await application.initialize()
    asyncio.create_task(application.start())

    port = int(os.getenv('PORT', 5000))
    await flask_app.run_task(host="0.0.0.0", port=port)

if name == 'main':
    asyncio.run(main())