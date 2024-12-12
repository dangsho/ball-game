import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters
import emoji  # برای بررسی ایموجی‌ها

# توکن ربات
TOKEN = '7899502015:AAHbkiEaoJG5cwUOQVUsnrrSGq7KdiGicWQ'
CHANNEL_ID = '@MusiccBikalam'  # یوزرنیم یا آیدی عددی کانال
APPEND_TEXT = """\n\n
@MusiccBikalam

🔻🔻🔻🔻
@Filmnam
@KashkoolH
"""

# تنظیمات لاگ
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# تابع برای بررسی اینکه متن فقط شامل ایموجی است
def contains_only_emoji(text: str) -> bool:
    stripped_text = text.strip()
    return all(char in emoji.EMOJI_DATA for char in stripped_text)

# تابع مدیریت پیام‌ها
async def handle_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        bot = context.bot
        message = update.message

        # جلوگیری از ارسال متن، ایموجی، استیکر و گیف
        if message.text and (contains_only_emoji(message.text) or message.text.strip()):
            await message.reply_text("متن‌ها و ایموجی‌ها به کانال ارسال نمی‌شوند.")
            logger.info("Text or emoji-only message ignored.")
            return

        if message.sticker:
            await message.reply_text("پیام‌های استیکر به کانال ارسال نمی‌شوند.")
            logger.info("Sticker message ignored.")
            return

        if message.animation:
            await message.reply_text("پیام‌های گیف به کانال ارسال نمی‌شوند.")
            logger.info("Animation (GIF) message ignored.")
            return

        # مدیریت عکس
        if message.photo:
            photo = message.photo[-1].file_id
            await bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=photo,
                caption=APPEND_TEXT  # حذف متن قبلی و افزودن متن جدید
            )
            logger.info("Photo message forwarded to channel with updated caption.")

        # مدیریت ویدیو
        elif message.video:
            video = message.video.file_id
            await bot.send_video(
                chat_id=CHANNEL_ID,
                video=video,
                caption=APPEND_TEXT  # حذف متن قبلی و افزودن متن جدید
            )
            logger.info("Video message forwarded to channel with updated caption.")

        # مدیریت فایل صوتی (موسیقی)
        elif message.audio:
            audio = message.audio.file_id
            await bot.send_audio(
                chat_id=CHANNEL_ID,
                audio=audio,
                caption=APPEND_TEXT  # حذف متن قبلی و افزودن متن جدید
            )
            logger.info("Audio message forwarded to channel with updated caption.")

        # مدیریت فایل‌های عمومی (مثل PDF)
        elif message.document:
            document = message.document.file_id
            await bot.send_document(
                chat_id=CHANNEL_ID,
                document=document,
                caption=APPEND_TEXT  # حذف متن قبلی و افزودن متن جدید
            )
            logger.info("Document message forwarded to channel with updated caption.")

        # ارسال پیام تایید به کاربر
        await message.reply_text("پیام شما با موفقیت پردازش شد!")

    except Exception as e:
        logger.error(f"Error handling message: {e}")
        await message.reply_text("خطایی رخ داد. لطفاً دوباره تلاش کنید.")

# تابع اصلی
async def main():
    application = Application.builder().token(TOKEN).build()

    # هندلر برای تمامی پیام‌ها
    application.add_handler(MessageHandler(filters.ALL, handle_all_messages))

    # اجرای ربات در حالت غیرمسدود کننده
    try:
        await application.run_polling(drop_pending_updates=True)
    except Exception as e:
        logger.error(f"Error in polling: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())