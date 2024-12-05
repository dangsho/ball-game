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

def get_crypto_price_from_coingecko(crypto_name):
    """دریافت قیمت ارز دیجیتال از کوین‌گکو"""
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={crypto_name}&vs_currencies=usd"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
        return {}

def get_crypto_price_from_nobitex(crypto_name):
    """دریافت قیمت ارز دیجیتال از نوبیتکس"""
    try:
        url = "https://api.nobitex.ir/market/stats"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json().get("stats", {})
            market_key = f"{crypto_name}-RLS"
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
        bitcoin_price = get_crypto_price_from_coingecko('bitcoin')
        ethereum_price = get_crypto_price_from_coingecko('ethereum')
        tether_price_toman = get_crypto_price_from_nobitex('usdt-rls')

        # ساختن متن پیام تاریخ و قیمت ثابت
        message = (
            f'@dangsho_bot\n\n'
            f"⏰ تهران:\n{tehran_time.strftime('%H:%M:%S')}\n\n"
            f"📅 تاریخ شمسی:\n{jalali_date.strftime('%Y/%m/%d')}\n\n"
            f"📅 تاریخ میلادی:\n{gregorian_date}\n\n"
            f"📅 تاریخ قمری:\n{hijri_date}\n\n"
            f"💰 قیمت ارزهای دیجیتال:\n"
            f"₿ بیت‌کوین: ${bitcoin_price}\n"
            f"Ξ اتریوم: ${ethereum_price}\n"
            f"💵 تتر: {tether_price_toman} تومان"
        )

        # لینک بازی
        game_url = "https://dangsho.github.io/ball-game/"

        # ساختن نتایج اینلاین
        results = [
            InlineQueryResultArticle(
                id="1",
                title="🎮 باز کردن لینک",
                input_message_content=InputTextMessageContent(f"تاریخ  را از این لینک باز کنید:\n{game_url}"),
                description="ارسال لینک ⏰"
            ),
            InlineQueryResultArticle(
                id="2",
                title="⏰ ارسال تاریخ و قیمت‌ها به چت",
                input_message_content=InputTextMessageContent(message),
                description="ارسال تاریخ و قیمت‌ ارزها به چت"
            ),
            InlineQueryResultArticle(
                id="3",
                title="💰 قیمت ارز از CoinGecko",
                input_message_content=InputTextMessageContent(
                    "🔍 برای دریافت قیمت ارز از کوین‌گکو، نام ارز را به انگلیسی وارد کنید."
                ),
                description="نام ارز موردنظر را وارد کنید."
            ),
            InlineQueryResultArticle(
                id="4",
                title="💵 قیمت ارز از Nobitex",
                input_message_content=InputTextMessageContent(
                    "🔍 برای دریافت قیمت ارز از نوبیتکس، نام ارز را به انگلیسی وارد کنید (مانند btc یا eth)."
                ),
                description="نام ارز موردنظر را وارد کنید."
            ),
        ]
        await update.inline_query.answer(results, cache_time=0)

    except ValueError as ve:
        logging.error(f"ValueError in inline query: {ve}")
    except Exception as e:
        logging.error(f"Error in inline query handler: {e}")
        # در صورت وقوع خطا، نتایج خالی را ارسال کنید.
        await update.inline_query.answer([], cache_time=0)

        # پردازش متن ورودی کاربر برای قیمت ارزها
        user_query = update.inline_query.query.lower().strip()
        if user_query:
            # بررسی و دریافت قیمت ارز از کوین‌گکو
            coingecko_price = get_crypto_price_from_coingecko(user_query)
            nobitex_price = get_crypto_price_from_nobitex(user_query)

            extra_results = [
                InlineQueryResultArticle(
                    id="coingecko",
                    title=f"💰 {user_query.upper()} در CoinGecko",
                    input_message_content=InputTextMessageContent(
                        f"💰 قیمت {user_query.upper()} به دلار: ${coingecko_price}"
                    ),
                    description=f"قیمت {user_query.upper()} به دلار"
                ),
                InlineQueryResultArticle(
                    id="nobitex",
                    title=f"💵 {user_query.upper()} در Nobitex",
                    input_message_content=InputTextMessageContent(
                        f"💵 قیمت {user_query.upper()} به تومان: {nobitex_price:,} تومان"
                    ),
                    description=f"قیمت {user_query.upper()} به تومان"
                ),
            ]

            # اضافه کردن نتایج جدید به پاسخ اینلاین
            results.extend(extra_results)

        # ارسال پاسخ به اینلاین کوئری با غیرفعال کردن کش
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

if __name__ == '__main__':
    asyncio.run(main())
