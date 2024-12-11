import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters

# توکن ربات
TOKEN ='7899502015:AAHbkiEaoJG5cwUOQVUsnrrSGq7KdiGicWQ'
CHANNEL_ID = '@MusiccBikalam'  # یوزرنیم یا آیدی عددی کانال
TOKEN = '7899502015:AAHbkiEaoJG5cwUOQVUsnrrSGq7KdiGicWQ'
# متن مورد نظر برای اضافه شدن به پیام
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


# تابع مدیریت انواع پیام‌ها
async def handle_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        bot = context.bot

        # مدیریت پیام متنی
        if update.message.text:
            await bot.send_message(
                chat_id=CHANNEL_ID,
                text=update.message.text + APPEND_TEXT
            )
            logger.info("Text message forwarded to channel.")

        # مدیریت عکس
        elif update.message.photo:
            # بزرگترین سایز عکس را انتخاب می‌کنیم
            photo = update.message.photo[-1].file_id
            caption = (update.message.caption or "") + APPEND_TEXT
            await bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=photo,
                caption=caption
            )
            logger.info("Photo message forwarded to channel.")

        # مدیریت ویدیو
        elif update.message.video:
            video = update.message.video.file_id
            caption = (update.message.caption or "") + APPEND_TEXT
            await bot.send_video(
                chat_id=CHANNEL_ID,
                video=video,
                caption=caption
            )
            logger.info("Video message forwarded to channel.")

        # مدیریت فایل صوتی (موسیقی)
        elif update.message.audio:
            audio = update.message.audio.file_id
            caption = (update.message.caption or "") + APPEND_TEXT
            await bot.send_audio(
                chat_id=CHANNEL_ID,
                audio=audio,
                caption=caption
            )
            logger.info("Audio message forwarded to channel.")

        # مدیریت فایل‌های عمومی (مثل PDF)
        elif update.message.document:
            document = update.message.document.file_id
            caption = (update.message.caption or "") + APPEND_TEXT
            await bot.send_document(
                chat_id=CHANNEL_ID,
                document=document,
                caption=caption
            )
            logger.info("Document message forwarded to channel.")

        # مدیریت استیکر
        elif update.message.sticker:
            sticker = update.message.sticker.file_id
            await bot.send_sticker(
                chat_id=CHANNEL_ID,
                sticker=sticker
            )
            logger.info("Sticker forwarded to channel.")

        # ارسال پیام تایید به کاربر
        await update.message.reply_text("پیام شما با موفقیت به کانال ارسال شد!")

    except Exception as e:
        logger.error(f"Error handling message: {e}")
        await update.message.reply_text("خطایی رخ داد. لطفاً دوباره تلاش کنید.")


# تابع اصلی
def main():
    application = Application.builder().token(TOKEN).build()

    # هندلر برای تمامی پیام‌ها
    application.add_handler(MessageHandler(filters.ALL, handle_all_messages))

    # اجرای ربات
    application.run_polling()


if __name__ == "__main__":
    main()