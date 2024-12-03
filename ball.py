import os
from quart import Quart, request
from telegram import Update, Bot, InlineQueryResultArticle, InputTextMessageContent, ParseMode
from telegram.ext import Application, CommandHandler, InlineQueryHandler
import sqlite3
import requests
import asyncio
import logging
import jdatetime
from datetime import datetime
from convertdate import islamic

# تنظیم لاگ‌ها با سطح DEBUG برای اشکال‌زدایی بهتر
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

if not TOKEN:
    print("TOKEN is not set in the environment variables.")
    raise ValueError("TOKEN is not set. Please set the token as an environment variable.")
    
bot = Bot(token=TOKEN)
application = Application.builder().token(TOKEN).build()
flask_app = Quart(__name__)

# اضافه کردن مسیر اصلی
@flask_app.route('/')
async def home():
    return "سرویس در حال اجرا است 🎉", 200

# هندلر /start
async def start(update: Update, context):
    try:
        now = jdatetime.datetime.now()
        gregorian_now = datetime.now()
        islamic_now = islamic.from_gregorian(gregorian_now.year, gregorian_now.month, gregorian_now.day)

        shamsi_date = now.strftime("%Y/%m/%d - %H:%M:%S")
        gregorian_date = gregorian_now.strftime("%Y/%m/%d - %H:%M:%S")
        islamic_date = f"{islamic_now[0]}/{islamic_now[1]}/{islamic_now[2]}"

        game_url = "https://dangsho.github.io/ball-game/"

        message = (
            f"برای شروع  روی لینک زیر کلیک کنید:\n"
            f"<a href='{game_url}'>🌟 بازی اینجا باز می‌شود</a>\n\n"
            f"⏰ <b>ساعت:</b> {now.strftime('%H:%M:%S')}\n"
            f"📅 <b>تاریخ‌ها:</b>\n"
            f"<b><font color='blue'>هجری شمسی:</font></b> {shamsi_date}\n"
            f"<b><font color='green'>میلادی:</font></b> {gregorian_date}\n"
            f"<b><font color='yellow'>قمری:</font></b> {islamic_date}"
        )

        await update.message.reply_text(message, parse_mode=ParseMode.HTML)
    except Exception as e:
        logging.error(f"Error in /start handler: {e}")
        await update.message.reply_text("متأسفیم، مشکلی پیش آمده است. لطفاً بعداً دوباره امتحان کنید.")

# هندلر اینلاین
async def inline_query(update: Update, context):
    try:
        now = jdatetime.datetime.now()
        gregorian_now = datetime.now()
        islamic_now = islamic.from_gregorian(gregorian_now.year, gregorian_now.month, gregorian_now.day)

        shamsi_date = now.strftime("%Y/%m/%d - %H:%M:%S")
        gregorian_date = gregorian_now.strftime("%Y/%m/%d - %H:%M:%S")
        islamic_date = f"{islamic_now[0]}/{islamic_now[1]}/{islamic_now[2]}"

        # ساختن نتیجه اینلاین
        results = [
            InlineQueryResultArticle(
                id="1",
                title="⏰ تاریخ و ساعت فعلی",
                input_message_content=InputTextMessageContent(
                    (
                        f"⏰ <b>ساعت:</b> {now.strftime('%H:%M:%S')}\n"
                        f"📅 <b>تاریخ‌ها:</b>\n"
                        f"<b><font color='blue'>هجری شمسی:</font></b> {shamsi_date}\n"
                        f"<b><font color='green'>میلادی:</font></b> {gregorian_date}\n"
                        f"<b><font color='yellow'>قمری:</font></b> {islamic_date}"
                    ),
                    parse_mode=ParseMode.HTML
                )
            )
        ]

        # ارسال پاسخ به اینلاین کوئری
        await update.inline_query.answer(results)
    except Exception as e:
        logging.error(f"Error in inline query handler: {e}")

# مسیر webhook
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
    response = requests.get(f"https://api.telegram.org/bot{TOKEN}/getWebhookInfo")
    logging.info("Webhook info: %s", response.json())

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