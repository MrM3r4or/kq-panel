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

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

# لاگ‌های عمومی (برای نمایش در پنل)
log_messages = []

def add_log(msg):
    ts = datetime.now().strftime('%H:%M:%S')
    log_messages.append(f"[{ts}] {msg}")
    print(log_messages[-1])
    if len(log_messages) > 500:
        log_messages.pop(0)

# دیکشنری برای نگهداری نمونه‌های در حال اجرای ربات‌ها
active_bots = {}

# ---------- توابع کمکی ----------
def get_bot_config(bot_id):
    return config.get_bot(bot_id)

def get_db_for(bot_id):
    return database.get_db()

# ---------- Handler های پایه (با bot_id) ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE, bot_id: int):
    user = update.effective_user
    args = context.args

    # ابتدا deep link
    if args:
        short_code = args[0]
        db = database.get_db()
        file = db.execute('SELECT * FROM file_links WHERE short_code=? AND bot_id=?', (short_code, bot_id)).fetchone()
        if file:
            try:
                await context.bot.send_document(chat_id=user.id, document=file['file_id'], caption=f"📄 {file['file_name']}")
            except Exception as e:
                await update.message.reply_text("❌ فایل در دسترس نیست.")
        else:
            await update.message.reply_text("❌ لینک نامعتبر.")
        return

    # بررسی بن
    if database.get_db().execute('SELECT 1 FROM banned_users WHERE user_id=? AND bot_id=?', (user.id, bot_id)).fetchone():
        await update.message.reply_text("⛔ شما بن شده‌اید.")
        return

    # ذخیره کاربر
    database.get_db().execute('INSERT OR IGNORE INTO users (user_id, first_name, last_name, username, bot_id) VALUES (?,?,?,?,?)',
                              (user.id, user.first_name, user.last_name, user.username, bot_id))
    database.get_db().commit()

    # جوین اجباری
    channels = database.get_db().execute('SELECT * FROM force_join WHERE bot_id=? AND enabled=1', (bot_id,)).fetchall()
    if channels:
        keyboard = []
        for ch in channels:
            keyboard.append([InlineKeyboardButton(f"📢 {ch['channel_name']}", url=f"https://t.me/{ch['channel_username']}")])
        keyboard.append([InlineKeyboardButton("✅ تایید عضویت", callback_data=f"check_join_{bot_id}")])
        await update.message.reply_text(
            channels[0]['custom_message'] or "⚠️ لطفاً در کانال‌های زیر عضو شوید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # پیام خوش‌آمدگویی و منو
    custom = database.get_db().execute('SELECT response_text FROM custom_messages WHERE bot_id=? AND command="/start"', (bot_id,)).fetchone()
    if custom:
        await update.message.reply_text(custom['response_text'])
    else:
        bot_type = get_bot_config(bot_id)['type']
        if bot_type == 'uploader':
            await update.message.reply_text("🎉 خوش آمدید! فایل ارسال کنید.",
                                            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("📁 ارسال فایل")]], resize_keyboard=True))
        elif bot_type == 'anonymous':
            await update.message.reply_text("👻 پیام ناشناس:\nپیام خود را بنویسید تا به ادمین ارسال شود.")
        elif bot_type == 'buy_sell':
            await update.message.reply_text("🛒 به ربات خرید و فروش خوش آمدید.")
    # نمایش دکمه‌های سفارشی
    btns = database.get_db().execute('SELECT * FROM custom_buttons WHERE bot_id=? AND menu_type="keyboard"', (bot_id,)).fetchall()
    if btns:
        kb = []
        row = []
        for i, btn in enumerate(btns):
            row.append(KeyboardButton(btn['button_text']))
            if len(row) == 2 or i == len(btns) - 1:
                kb.append(row)
                row = []
        await update.message.reply_text("⬇️ منو:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def check_join(update: Update, context: ContextTypes.DEFAULT_TYPE, bot_id: int):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    channels = database.get_db().execute('SELECT * FROM force_join WHERE bot_id=? AND enabled=1', (bot_id,)).fetchall()
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
        keyboard.append([InlineKeyboardButton("🔄 بررسی مجدد", callback_data=f"check_join_{bot_id}")])
        await query.edit_message_text("❌ هنوز عضو همه کانال‌ها نیستید.", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await query.edit_message_text("✅ تأیید شد! اکنون می‌توانید از ربات استفاده کنید.")
        # بعد از تأیید جوین، دوباره استارت کن (بدون deep link)
        await start(update, context, bot_id=bot_id)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE, bot_id: int):
    msg = update.message
    user = update.effective_user
    if not msg:
        return

    # بررسی بن
    if database.get_db().execute('SELECT 1 FROM banned_users WHERE user_id=? AND bot_id=?', (user.id, bot_id)).fetchone():
        await msg.reply_text("⛔ شما بن شده‌اید.")
        return

    # ذخیره کاربر
    database.get_db().execute('INSERT OR IGNORE INTO users (user_id, first_name, last_name, username, bot_id) VALUES (?,?,?,?,?)',
                              (user.id, user.first_name, user.last_name, user.username, bot_id))
    database.get_db().commit()

    bot_config = get_bot_config(bot_id)
    bot_type = bot_config['type'] if bot_config else 'uploader'

    # پردازش فایل (برای آپلودر)
    if bot_type == 'uploader':
        file = msg.document or msg.video or msg.audio or (msg.photo[-1] if msg.photo else None) or msg.voice
        if file:
            name = file.file_name if hasattr(file, 'file_name') and file.file_name else f"file_{file.file_unique_id}"
            typ = 'document' if msg.document else 'video' if msg.video else 'audio' if msg.audio else 'photo' if msg.photo else 'voice'
            try:
                fobj = await context.bot.get_file(file.file_id)
                folder = bot_config['folder']
                os.makedirs(folder, exist_ok=True)
                path = os.path.join(folder, name)
                await fobj.download_to_drive(path)
                code = secrets.token_hex(4)
                db = database.get_db()
                db.execute('INSERT INTO files (bot_id, file_id, file_name, file_type) VALUES (?,?,?,?)',
                           (bot_id, file.file_id, name, typ))
                db.execute('INSERT INTO file_links (bot_id, short_code, file_id, file_name) VALUES (?,?,?,?)',
                           (bot_id, code, file.file_id, name))
                db.commit()
                me = await context.bot.get_me()
                link = f"https://t.me/{me.username}?start={code}"
                await msg.reply_text(f"✅ ذخیره شد!\n🔗 {link}")
            except Exception as e:
                await msg.reply_text(f"❌ خطا: {e}")
            return

    # پردازش پیام متنی
    if msg.text:
        # بررسی دکمه‌های منو
        if msg.text == "📁 ارسال فایل" and bot_type == 'uploader':
            await msg.reply_text("📁 فایل خود را ارسال کنید.")
            return

        # دستورات سفارشی
        custom = database.get_db().execute('SELECT response_text FROM custom_messages WHERE bot_id=? AND command=?',
                                           (bot_id, msg.text)).fetchone()
        if custom:
            await msg.reply_text(custom['response_text'])
        else:
            if bot_type == 'anonymous':
                # ذخیره پیام ناشناس
                database.get_db().execute('INSERT INTO anon_messages (bot_id, owner_chat_id, sender_chat_id, message_text) VALUES (?,?,?,?)',
                                          (bot_id, 0, user.id, msg.text))  # owner باید از تنظیمات خوانده شود
                database.get_db().commit()
                await msg.reply_text("✅ پیام شما ناشناس ارسال شد.")
            else:
                await msg.reply_text("📁 لطفاً فایل ارسال کنید.")
    else:
        await msg.reply_text("📁 فقط فایل پشتیبانی می‌شود.")

# ---------- اجرا و توقف ----------
def run_bot(bot_id: int):
    """اجرای ربات با bot_id مشخص"""
    bot_config = get_bot_config(bot_id)
    if not bot_config:
        add_log(f"❌ بات با آیدی {bot_id} یافت نشد.")
        return

    token = bot_config['token']
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def main():
        app = Application.builder().token(token).build()
        # هندلرها را با bot_id پارشیال می‌کنیم
        from functools import partial
        app.add_handler(CommandHandler("start", lambda u, c: start(u, c, bot_id=bot_id)))
        app.add_handler(CallbackQueryHandler(lambda u, c: check_join(u, c, bot_id=bot_id), pattern=f"^check_join_{bot_id}$"))
        app.add_handler(MessageHandler(filters.ALL, lambda u, c: handle_message(u, c, bot_id=bot_id)))

        add_log(f"✅ ربات {bot_id} شروع به کار کرد.")
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        # حلقه نگه‌دارنده (تا زمانی که متوقف نشده)
        while bot_id in active_bots:
            await asyncio.sleep(1)
        add_log(f"🛑 ربات {bot_id} در حال توقف...")
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

    try:
        loop.run_until_complete(main())
    except Exception as e:
        add_log(f"💀 خطا در ربات {bot_id}: {e}")
    finally:
        loop.close()
        active_bots.pop(bot_id, None)

def start_bot(bot_id: int):
    """شروع ربات در یک ترد جدا"""
    if bot_id in active_bots:
        add_log(f"⚠️ ربات {bot_id} قبلاً در حال اجراست.")
        return
    active_bots[bot_id] = True
    t = threading.Thread(target=run_bot, args=(bot_id,), daemon=True)
    t.start()

def stop_bot(bot_id: int):
    """توقف ربات"""
    if bot_id in active_bots:
        add_log(f"🛑 درخواست توقف ربات {bot_id}")
        active_bots.pop(bot_id, None)  # باعث خروج از حلقه می‌شود
        return True
    return False