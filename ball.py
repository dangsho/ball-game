import os
from quart import Quart, request
from telegram import Update, Bot, InlineQueryResultCachedPhoto
from telegram.ext import Application, CommandHandler, InlineQueryHandler
import sqlite3
import asyncio
import logging
from io import BytesIO
from pyppeteer import launch
from pytz import timezone
import datetime

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
GAME_URL = "https://dangsho.github.io/ball-game/"

if not TOKEN:
    raise ValueError("TOKEN is not set. Please set the token as an environment variable.")

bot = Bot(token=TOKEN)
application = Application.builder().token(TOKEN).build()
flask_app = Quart(__name__)

@flask_app.route('/')
async def home():
    return "سرویس در حال اجرا است 🎉", 200

async def start(update: Update, context):
    try:
        game_url = "https://dangsho.github.io/ball-game/"
        await update.message.reply_text(f" برای دیدن تاریخ کلیک کنید:\n{game_url}")
    except Exception as e:
        logging.error(f"Error in /start handler: {e}")
        await update.message.reply_text("متأسفیم، مشکلی پیش آمده است.")
        
async def capture_screenshot_to_memory(url):
    """گرفتن اسکرین‌شات از یک URL و ذخیره در حافظه"""
    try:
        browser = await launch()
        page = await browser.newPage()
        await page.goto(url)
        screenshot_buffer = BytesIO()
        await page.screenshot({'path': None, 'fullPage': True, 'encoding': 'binary'})
        screenshot_buffer.seek(0)
        await browser.close()
        return screenshot_buffer
    except Exception as e:
        logging.error(f"Error capturing screenshot: {e}")
        return None


async def upload_photo_to_telegram(bot, buffer):
    """آپلود موقت تصویر به تلگرام"""
    try:
        response = await bot.upload_media(buffer, media_type="photo")
        return response.file_id
    except Exception as e:
        logging.error(f"Error uploading photo to Telegram: {e}")
        return None


async def inline_query(update: Update, context):
    try:
        # گرفتن اسکرین‌شات در حافظه
        screenshot = await capture_screenshot_to_memory(GAME_URL)
        if not screenshot:
            await update.inline_query.answer([], cache_time=0)
            return

        # آپلود تصویر به تلگرام و دریافت file_id
        file_id = await upload_photo_to_telegram(bot, screenshot)
        if not file_id:
            await update.inline_query.answer([], cache_time=0)
            return

        # ایجاد پاسخ اینلاین با فایل آپلود شده
        results = [
            InlineQueryResultCachedPhoto(
                id="1",
                photo_file_id=file_id,
                caption="📷 اسکرین‌شات بازی",
            )
        ]

        # ارسال پاسخ اینلاین
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