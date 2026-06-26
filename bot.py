import logging
import sys
import os
import asyncio
import threading
import secrets
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import config
import database

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

log_messages = []
def add_log(message):
    timestamp = datetime.now().strftime('%H:%M:%S')
    log_entry = f"[{timestamp}] {message}"
    log_messages.append(log_entry)
    print(log_entry)
    if len(log_messages) > 500:
        log_messages.pop(0)

application = None
stop_event = threading.Event()
bot_username = None

# ========== Database helpers ==========
def is_user_banned(user_id):
    conn = database.get_db()
    banned = conn.execute('SELECT user_id FROM banned_users WHERE user_id=?', (user_id,)).fetchone()
    conn.close()
    return banned is not None

def save_user(user):
    conn = database.get_db()
    conn.execute('INSERT OR IGNORE INTO users (user_id, first_name, last_name, username) VALUES (?,?,?,?)',
                 (user.id, user.first_name, user.last_name, user.username))
    conn.commit()
    conn.close()

def get_force_join_channels():
    conn = database.get_db()
    channels = conn.execute('SELECT * FROM force_join WHERE enabled=1').fetchall()
    conn.close()
    return channels

def get_keyboard_buttons():
    conn = database.get_db()
    buttons = conn.execute("SELECT * FROM custom_buttons WHERE menu_type='keyboard' ORDER BY priority").fetchall()
    conn.close()
    return buttons

def get_custom_message(command):
    conn = database.get_db()
    msg = conn.execute('SELECT * FROM custom_messages WHERE command=?', (command,)).fetchone()
    conn.close()
    return msg

def save_file_link(short_code, file_id, file_name):
    conn = database.get_db()
    conn.execute('INSERT INTO file_links (short_code, file_id, file_name) VALUES (?,?,?)',
                 (short_code, file_id, file_name))
    conn.commit()
    conn.close()

def get_file_by_short_code(short_code):
    conn = database.get_db()
    file = conn.execute('SELECT * FROM file_links WHERE short_code=?', (short_code,)).fetchone()
    conn.close()
    return file

# ========== Handlers ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args

    # Deep link file handling
    if args:
        short_code = args[0]
        add_log(f"🔗 Deep link code {short_code} from user {user.id}")
        file_data = get_file_by_short_code(short_code)
        if file_data:
            try:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=file_data['file_id'],
                    caption=f"📄 {file_data['file_name']}"
                )
                add_log(f"✅ File sent to user {user.id}")
                return
            except Exception as e:
                add_log(f"❌ Error sending file: {e}")
                await update.message.reply_text("❌ فایل مورد نظر یافت نشد یا حذف شده است.")
                return
        else:
            await update.message.reply_text("❌ لینک نامعتبر است.")
            return

    # Normal start
    add_log(f"👤 /start from {user.first_name} ({user.id})")
    if is_user_banned(user.id):
        await update.message.reply_text("⛔ شما بن شده‌اید!")
        return

    save_user(user)

    # Force join check
    channels = get_force_join_channels()
    if channels:
        keyboard = []
        for ch in channels:
            keyboard.append([InlineKeyboardButton(f"📢 {ch['channel_name']}", url=f"https://t.me/{ch['channel_username']}")])
        keyboard.append([InlineKeyboardButton("✅ تایید عضویت", callback_data="check_join")])
        msg_text = channels[0]['custom_message'] if channels[0]['custom_message'] else "⚠️ برای استفاده از ربات، ابتدا در کانال‌های زیر عضو شوید:"
        await update.message.reply_text(msg_text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # No force join → show appropriate message
    custom_start = get_custom_message("/start")
    if custom_start:
        await update.message.reply_text(custom_start['response_text'])
    else:
        await default_welcome(update)

    # Show main keyboard
    await show_main_keyboard(update)

async def default_welcome(update: Update):
    """Default welcome message with an upload button."""
    kb = [[KeyboardButton("📁 ارسال فایل")]]
    await update.message.reply_text(
        "🎉 به ربات آپلودر فایل خوش آمدید!\n"
        "برای دریافت لینک اختصاصی، روی دکمه زیر کلیک کنید و فایل خود را ارسال نمایید.",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )

async def check_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    channels = get_force_join_channels()
    not_joined = []
    for ch in channels:
        try:
            member = await context.bot.get_chat_member(f"@{ch['channel_username']}", user_id)
            if member.status in ['left', 'kicked', 'restricted']:
                not_joined.append(ch)
        except:
            not_joined.append(ch)

    if not_joined:
        keyboard = []
        for ch in channels:
            keyboard.append([InlineKeyboardButton(f"📢 {ch['channel_name']}", url=f"https://t.me/{ch['channel_username']}")])
        keyboard.append([InlineKeyboardButton("🔄 بررسی مجدد", callback_data="check_join")])
        await query.edit_message_text("❌ هنوز در همه کانال‌ها عضو نشده‌اید!", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        add_log(f"✅ تایید شد: {user_id}")
        await query.edit_message_text("✅ عضویت تایید شد! 🎉")
        # Show main menu
        custom_start = get_custom_message("/start")
        if custom_start:
            await context.bot.send_message(chat_id=query.message.chat_id, text=custom_start['response_text'])
        else:
            await context.bot.send_message(chat_id=query.message.chat_id, text="🎉 خوش آمدید! حالا می‌توانید فایل ارسال کنید.")
        await show_main_keyboard_message(context.bot, query.message.chat_id)

async def show_main_keyboard(update: Update):
    buttons = get_keyboard_buttons()
    if buttons:
        kb = []
        row = []
        for i, btn in enumerate(buttons):
            row.append(KeyboardButton(btn['button_text']))
            if len(row) == 2 or i == len(buttons) - 1:
                kb.append(row)
                row = []
        await update.message.reply_text("⬇️ منوی اصلی:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    else:
        # Fallback to upload button
        kb = [[KeyboardButton("📁 ارسال فایل")]]
        await update.message.reply_text("⬇️ برای شروع فایل ارسال کنید:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def show_main_keyboard_message(bot, chat_id):
    buttons = get_keyboard_buttons()
    if buttons:
        kb = []
        row = []
        for i, btn in enumerate(buttons):
            row.append(KeyboardButton(btn['button_text']))
            if len(row) == 2 or i == len(buttons) - 1:
                kb.append(row)
                row = []
        await bot.send_message(chat_id=chat_id, text="⬇️ منوی اصلی:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    else:
        kb = [[KeyboardButton("📁 ارسال فایل")]]
        await bot.send_message(chat_id=chat_id, text="⬇️ برای شروع فایل ارسال کنید:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not update.message:
        return
    if is_user_banned(user.id):
        await update.message.reply_text("⛔ شما بن شده‌اید!")
        return
    save_user(user)

    file = None
    file_name = None
    file_type = None

    if update.message.document:
        file = update.message.document
        file_name = file.file_name or f"doc_{file.file_unique_id}"
        file_type = "سند"
    elif update.message.video:
        file = update.message.video
        file_name = f"video_{file.file_unique_id}.mp4"
        file_type = "ویدیو"
    elif update.message.audio:
        file = update.message.audio
        file_name = file.file_name or f"audio_{file.file_unique_id}.mp3"
        file_type = "صوت"
    elif update.message.photo:
        file = update.message.photo[-1]
        file_name = f"photo_{file.file_unique_id}.jpg"
        file_type = "تصویر"
    elif update.message.voice:
        file = update.message.voice
        file_name = f"voice_{file.file_unique_id}.ogg"
        file_type = "ویس"
    else:
        # Text message
        text = update.message.text
        if text == "📁 ارسال فایل":
            await update.message.reply_text("📁 لطفاً فایل خود را ارسال کنید.")
        else:
            custom_msg = get_custom_message(text)
            if custom_msg:
                add_log(f"💬 Custom command: {text}")
                await update.message.reply_text(custom_msg['response_text'])
            else:
                await update.message.reply_text("📁 لطفاً فایل ارسال کنید.")
        return

    if file:
        add_log(f"📁 {file_type}: {file_name} from {user.first_name}")
        try:
            status_msg = await update.message.reply_text("⏳ در حال دریافت فایل...")
            file_obj = await context.bot.get_file(file.file_id)
            os.makedirs(config.Config.UPLOAD_FOLDER, exist_ok=True)
            file_path = os.path.join(config.Config.UPLOAD_FOLDER, file_name)
            await file_obj.download_to_drive(file_path)

            # Save to files table
            conn = database.get_db()
            conn.execute('INSERT INTO files (file_id, file_name, file_type, message_id, chat_id) VALUES (?,?,?,?,?)',
                         (file.file_id, file_name, file_type, update.message.message_id, update.effective_chat.id))
            conn.commit()
            conn.close()

            # Generate short code
            short_code = secrets.token_hex(4)
            save_file_link(short_code, file.file_id, file_name)

            global bot_username
            if not bot_username:
                me = await context.bot.get_me()
                bot_username = me.username

            share_link = f"https://t.me/{bot_username}?start={short_code}"

            await status_msg.edit_text(
                f"✅ **فایل با موفقیت ذخیره شد!**\n\n"
                f"📄 نام: `{file_name}`\n"
                f"📦 نوع: {file_type}\n"
                f"🔗 لینک اختصاصی:\n`{share_link}`\n\n"
                f"👥 با این لینک هر کسی میتونه فایل رو دریافت کنه.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔗 دریافت فایل", url=share_link)]
                ])
            )
            add_log(f"✅ File saved: {file_name} | code: {short_code}")
        except Exception as e:
            add_log(f"❌ Error saving file: {e}")
            await update.message.reply_text(f"❌ خطا در ذخیره فایل: {str(e)[:200]}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    add_log(f"❌ System error: {context.error}")

# ========== Bot runner ==========
def run_bot():
    global application, stop_event, bot_username
    add_log("🚀 Starting bot...")
    if not config.Config.BOT_TOKEN:
        add_log("❌ No token set!")
        return

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    stop_event.clear()

    async def start_app():
        global application, bot_username
        app = Application.builder().token(config.Config.BOT_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(check_join, pattern="^check_join$"))
        app.add_handler(MessageHandler(filters.ALL, handle_message))
        app.add_error_handler(error_handler)
        application = app
        me = await app.bot.get_me()
        bot_username = me.username
        add_log(f"✅ Bot @{bot_username} ready!")
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)

        while not stop_event.is_set():
            await asyncio.sleep(1)

        add_log("🛑 Shutting down...")
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        application = None

    try:
        loop.run_until_complete(start_app())
    except Exception as e:
        add_log(f"💀 Fatal error: {e}")
    finally:
        loop.close()
        add_log("⏹️ Bot stopped")

def stop_bot():
    global stop_event
    if application:
        add_log("Sending stop signal...")
        stop_event.set()
        return True
    return False