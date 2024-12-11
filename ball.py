from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.background import BackgroundScheduler
import os
from quart import Quart, request
from telegram.constants import ChatMemberStatus
from telegram.ext import ContextTypes
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
import shutil
from async_timeout import timeout


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

# مسیرهای پایدار برای دیتابیس و بک‌آپ
DATABASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "crypto_bot.db"))
BACKUP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "backups"))

if os.access(DATABASE, os.W_OK):
    print(f"Write access to the database path is available.")
else:
    print(f"Write access to the database path is not available.")
    
ADMIN_CHAT_ID = 48232573
CHANNEL_ID = "@coin_btcc"  # آیدی کانال تلگرام (باید با @ شروع شود)
CRYPTO_LIST = ["BTC", "ETH", "DOGE", "SHIB", "XRP", "TRX", "DOGS", "NOT", "X", "MAJOR"]  # لیست ارزهایی که قیمت آن‌ها ارسال می‌شود

if not TOKEN:
    raise ValueError("TOKEN is not set. Please set the token as an environment variable.")

bot = Bot(token=TOKEN)
application = Application.builder().token(TOKEN).build()
flask_app = Quart(__name__)


# تابع ارسال قیمت ارزها به کانال تلگرام

# --- تابع ارسال قیمت‌ها به کانال ---

async def send_crypto_prices():
    try:
        response_message = "💰 قیمت لحظه‌ای ارزهای دیجیتال:\n"
        
            
        for crypto_name in CRYPTO_LIST:
            try:
                cmc_price, percent_change_24h = get_crypto_price_from_coinmarketcap(crypto_name.upper())
                usdt_to_irr = get_usdt_to_irr_price(crypto_name.lower())
              

                # بررسی داده‌های بازگشتی
                if cmc_price is None or percent_change_24h is None:
                    response_message += f"- {crypto_name.upper()}: ⚠️ داده نامعتبر.\n"
                    continue

                # تبدیل مقادیر به float و بررسی صحت آن‌ها
                try:
                    cmc_price = float(cmc_price)
                    percent_change_24h = float(percent_change_24h)
                    usdt_to_irr = float(usdt_to_irr)

                    arrow = "🟢" if percent_change_24h > 0 else "🔴"
                    response_message += (
                    f"- {crypto_name.upper()}: ${cmc_price} | {arrow} {abs(percent_change_24h):.2f}% \n ⬅️{usdt_to_irr:,.0f} ریال \n\n"
                )
                except (ValueError, TypeError):
                    response_message += f"- {crypto_name.upper()}: ⚠️ داده نامعتبر.\n"

            except Exception as e:
                logging.error(f"Error fetching price for {crypto_name}: {e}")
                response_message += f"- {crypto_name.upper()}: ⚠️ خطا در دریافت قیمت.\n"
                

        response_message += "\n\nورود به ربات قیمت‌گیری به تومن و دلار\n@dangsho_bot"
       
        await bot.send_message(chat_id=CHANNEL_ID, text=response_message)
    except Exception as e:
        logging.error(f"Error in send_crypto_prices: {e}")

# زمان‌بندی ارسال قیمت‌ها هر 1 دقیقه
def schedule_price_updates():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_crypto_prices, "interval", minutes=3)  # اجرای هر 1 دقیقه
    scheduler.start()
    
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


def get_crypto_price_from_coinmarketcap(crypto_symbol):

    """دریافت قیمت ارز دیجیتال از نوبیتکس"""
    symbol = str(crypto_symbol).lower()  # تبدیل نماد ارز به حروف کوچک برای سازگاری با نوبیتکس
    try:
        # URL برای دریافت قیمت از API نوبیتکس
        url = "https://api.nobitex.ir/market/stats"

        # پارامترهای درخواست به API
        params = {
            "srcCurrency": symbol,
            "dstCurrency": "usdt"  # دلار تتر
        }

        response = requests.get(url, params=params)
        response.raise_for_status()  # بررسی هرگونه خطای HTTP
        data = response.json()

        # بررسی وجود نماد مورد نظر در پاسخ API
        if f"{symbol}-usdt" not in data["stats"]:
            logging.error(f"Symbol {symbol} not found in Nobitex response.")
            return None, None

        # دریافت قیمت و درصد تغییرات 24 ساعته
        price = data["stats"][f"{symbol}-usdt"]["latest"]
        percent_change_24h = data["stats"][f"{symbol}-usdt"]["dayChange"]

        # تبدیل قیمت به float برای مقایسه
        price = float(price)

        # محدود کردن اعشار بر اساس شرط
        if price > 1:
            price = f"{price:.2f}"  # 2 رقم اعشار برای قیمت بالای 1 دلار
        else:
            price = f"{price:.8f}"  # 8 رقم اعشار برای قیمت‌های کوچک‌تر

        # تبدیل درصد تغییرات به float
        percent_change_24h = float(percent_change_24h)

        return price, percent_change_24h

    except requests.RequestException as e:
        logging.error(f"Error fetching data from Nobitex: {e}")
        return None, None




async def get_crypto_price_direct(update: Update, context):
    """ارسال قیمت ارز دیجیتال با ارسال مستقیم نام ارز"""
    try:
        crypto_name = update.message.text.strip().upper()
        await notify_admin(
            user_id=update.message.from_user.id, username=update.message.from_user.username
        )
        
        BLOCKED_WORDS = ["USER", "ADD", "DEL", "LIST", "ONTIME", "تاریخ"]
        if crypto_name in BLOCKED_WORDS or " " in crypto_name:
            # اگر کلمه در لیست بلاک‌شده‌ها باشد، تابع متوقف شود
            return

        cmc_price, percent_change_24h = get_crypto_price_from_coinmarketcap(crypto_name)
        nobitex_price = get_usdt_to_irr_price(crypto_name.lower())

        if cmc_price or nobitex_price:
            response_message = f"💰 قیمت {crypto_name}:\n"
            if cmc_price is not None:
                # اضافه کردن فلش سبز یا قرمز
                arrow = "🟢" if percent_change_24h > 0 else "🔴"
                response_message += (
                    f"-نوبیتکس دلار: ${cmc_price} {arrow} {abs(percent_change_24h):.2f}%\n"
                )
            if nobitex_price:
                response_message += f"-نوبیتکس ریال: {nobitex_price:,} ریال\n"
            await update.message.reply_text(response_message)
        else:
            return
        	
    except Exception as e:
        logging.error(f"Error in direct price fetch: {e}")
        
        

async def inline_query(update: Update, context):
    try:
        
        # بررسی وجود inline_query
        if not update.inline_query:
            logging.error("Inline query is None.")
            return
            
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
    # جدول کاربران
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT
        )
    ''')
    conn.commit()
    conn.close()

# ثبت کاربران در دیتابیس
def register_user(user_id, username):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
    conn.commit()
    conn.close()

# شمارش کاربران
def get_user_count():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    user_count = c.fetchone()[0]
    conn.close()
    return user_count

async def handle_user(update: Update, context):
    # بررسی اینکه آیا effective_user مقدار دارد
    if update.effective_user is None:
        logging.warning("Effective user is None. Skipping this update.")
        return

    try:
        user_id = update.effective_user.id
        username = update.effective_user.username

        # ثبت کاربر در دیتابیس
        register_user(user_id, username)

        # اگر پیام "user" باشد، تعداد کاربران را نمایش بده
        if update.message and update.message.text.strip().lower() == "user":
            if user_id == ADMIN_CHAT_ID:  # فقط مدیر اجازه مشاهده دارد
                user_count = get_user_count()
                await update.message.reply_text(f"📊 تعداد کاربران: {user_count}")
            else:
                await update.message.reply_text("⛔ شما مجاز به استفاده از این دستور نیستید.")
        else:
        	await get_crypto_price_direct(update, context)
# نمایش تعداد کاربران با فرمان /stats
    except Exception as e:
        logging.error(f"Error in handle_user: {e}")

async def show_stats(update: Update, context):
    if update.effective_user.id == ADMIN_CHAT_ID:  # فقط مدیر اجازه مشاهده دارد
        user_count = get_user_count()
        await update.message.reply_text(f"📊 تعداد کاربران: {user_count}")
    else:
        await update.message.reply_text("⛔ شما مجاز به استفاده از این دستور نیستید.")
        
async def forward_message_to_admin(update: Update, context):
    """
    ارسال پیام کاربر به مدیر
    """
    try:
        # اطلاعات پیام کاربر
        user_id = update.effective_user.id
        username = update.effective_user.username
        message_text = update.message.text

        # ساخت پیام برای ارسال به مدیر
        message_to_admin = f"🔔 پیام جدید از کاربر:\n\n👤 آیدی: {user_id}\n"
        if username:
            message_to_admin += f"📛 نام کاربری: @{username}\n"
        message_to_admin += f"💬 پیام:\n{message_text}"

        # ارسال پیام به مدیر
        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=message_to_admin)

    except Exception as e:
        logging.error(f"Error forwarding message to admin: {e}")

# به‌روزرسانی handler پیام‌ها
async def handle_message(update: Update, context):
    try:
        # فوروارد کردن پیام به مدیر
        await forward_message_to_admin(update, context)

        # مدیریت سایر دستورها و درخواست‌ها   
        
        message = update.message.text.strip().split(maxsplit=1)
        command = message[0].lower()  # استخراج دستور (add, del, list)
        argument = message[1].upper() if len(message) > 1 else None  # استخراج نام ارز (در صورت وجود)

        user_id = update.effective_user.id
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()

        if command == "add":
            if not argument:
                await update.message.reply_text("❗️ دستور صحیح: add <نام_ارز>")
                return
            c.execute("INSERT OR IGNORE INTO user_cryptos (user_id, crypto_symbol) VALUES (?, ?)", (user_id, argument))
            conn.commit()
            await update.message.reply_text(f"✅ ارز {argument} به لیست شما اضافه شد.")
        
        elif command == "del":
            if not argument:
                await update.message.reply_text("❗️ دستور صحیح: del <نام_ارز>")
                return
            c.execute("DELETE FROM user_cryptos WHERE user_id = ? AND crypto_symbol = ?", (user_id, argument))
            conn.commit()
            await update.message.reply_text(f"✅ ارز {argument} از لیست شما حذف شد.")
        
        elif command == "list":
            c.execute("SELECT crypto_symbol FROM user_cryptos WHERE user_id = ?", (user_id,))
            cryptos = [row[0] for row in c.fetchall()]
            if not cryptos:
                await update.message.reply_text("ℹ️ لیست شما خالی است. از دستور add برای اضافه کردن ارز استفاده کنید.")
            else:
                response = "💰 لیست ارزهای شما:\n"
                for crypto in cryptos:
                    price = get_crypto_price_from_coinmarketcap(crypto)
                    response += f"- {crypto}: ${price if price else 'نامشخص'}\n"
                await update.message.reply_text(response)
        
        else:
            # اگر دستور ناهماهنگ باشد، به‌صورت پیش‌فرض قیمت را جستجو کن
            await get_crypto_price_direct(update, context)

        conn.close()

    except Exception as e:
        logging.error(f"Error in handle_message: {e}")
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

# تابع اصلی برای راه‌اندازی برنامه___________

async def main():
    # پیکربندی لاگینگ
    logging.basicConfig(level=logging.INFO)

    # راه‌اندازی دیتابیس
    setup_database()  # اگر async نیست، بدون await فراخوانی کنید
   

    # افزودن هندلرها به application
    application.add_handler(MessageHandler(filters.Regex(r'^user$'), handle_user))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CommandHandler("stats", show_stats))
    application.add_handler(InlineQueryHandler(inline_query))

    # تنظیم Webhook
    await set_webhook()

    # اجرای زمان‌بندی ارسال قیمت‌ها
    schedule_price_updates()  # نیازی به await ندارد، زیرا معمولاً sync است
    
    # آماده‌سازی و اجرای application
    await application.initialize()
    await application.start()

    # اجرای Flask (سازگار با asyncio)
    port = int(os.getenv('PORT', 5000))
    await flask_app.run_task(host="0.0.0.0", port=port)

async def shutdown():
    await application.stop()
    logging.info("Application stopped.")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        asyncio.run(shutdown())