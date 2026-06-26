import logging, sys, os, asyncio, threading, secrets
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import config, database

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO, handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)

# لاگ‌های ذخیره‌شونده
log_messages = []
def add_log(msg):
    ts = datetime.now().strftime('%H:%M:%S')
    log_messages.append(f"[{ts}] {msg}")
    print(log_messages[-1])
    if len(log_messages) > 500: log_messages.pop(0)

# متغیرهای گلوبال
application = None
stop_event = threading.Event()
bot_username = None

# توابع دیتابیس
def is_banned(uid):
    c = database.get_db().execute('SELECT 1 FROM banned_users WHERE user_id=?',(uid,)).fetchone(); c.close(); return bool(c)

def save_user(u):
    db = database.get_db(); db.execute('INSERT OR IGNORE INTO users (user_id,first_name,last_name,username) VALUES (?,?,?,?)',(u.id,u.first_name,u.last_name,u.username)); db.commit(); db.close()

def get_force_channels():
    c = database.get_db().execute('SELECT * FROM force_join WHERE enabled=1').fetchall(); c.close(); return c

def get_keyboard_buttons():
    c = database.get_db().execute("SELECT * FROM custom_buttons WHERE menu_type='keyboard' ORDER BY priority").fetchall(); c.close(); return c

def get_custom_msg(cmd):
    c = database.get_db().execute('SELECT * FROM custom_messages WHERE command=?',(cmd,)).fetchone(); c.close(); return c

def save_link(code, fid, name):
    db = database.get_db(); db.execute('INSERT INTO file_links (short_code,file_id,file_name) VALUES (?,?,?)',(code,fid,name)); db.commit(); db.close()

def get_file_by_code(code):
    c = database.get_db().execute('SELECT * FROM file_links WHERE short_code=?',(code,)).fetchone(); c.close(); return c

# Handlerها
async def start(update, context):
    user = update.effective_user
    args = context.args
    if args:
        code = args[0]
        add_log(f"🔗 Deep link code {code}")
        file = get_file_by_code(code)
        if file:
            try:
                await context.bot.send_document(chat_id=user.id, document=file['file_id'], caption=f"📄 {file['file_name']}")
            except:
                await update.message.reply_text("❌ فایل حذف شده است.")
        else:
            await update.message.reply_text("❌ لینک نامعتبر.")
        return

    add_log(f"👤 /start {user.id}")
    if is_banned(user.id): await update.message.reply_text("⛔ بن شدی"); return
    save_user(user)
    chs = get_force_channels()
    if chs:
        kb = []
        for ch in chs:
            kb.append([InlineKeyboardButton(f"📢 {ch['channel_name']}", url=f"https://t.me/{ch['channel_username']}")])
        kb.append([InlineKeyboardButton("✅ تایید", callback_data="check_join")])
        await update.message.reply_text(chs[0]['custom_message'] or "⚠️ عضو شوید:", reply_markup=InlineKeyboardMarkup(kb))
        return
    # بدون جوین
    cm = get_custom_msg("/start")
    if cm:
        await update.message.reply_text(cm['response_text'])
    else:
        await update.message.reply_text("🎉 خوش آمدید! فایل ارسال کنید.", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("📁 ارسال فایل")]], resize_keyboard=True))
    await show_main_menu(update)

async def check_join(update, context):
    q = update.callback_query; await q.answer(); uid = q.from_user.id
    chs = get_force_channels(); bad = []
    for ch in chs:
        try:
            m = await context.bot.get_chat_member(f"@{ch['channel_username']}", uid)
            if m.status in ['left','kicked']: bad.append(ch)
        except: bad.append(ch)
    if bad:
        kb = [[InlineKeyboardButton(f"📢 {ch['channel_name']}", url=f"https://t.me/{ch['channel_username']}")] for ch in chs]
        kb.append([InlineKeyboardButton("🔄 بررسی", callback_data="check_join")])
        await q.edit_message_text("❌ عضو نیستی", reply_markup=InlineKeyboardMarkup(kb))
    else:
        await q.edit_message_text("✅ تایید شد")
        cm = get_custom_msg("/start")
        txt = cm['response_text'] if cm else "🎉 حالا فایل بفرست"
        await context.bot.send_message(q.message.chat_id, txt)
        await show_main_menu_msg(context.bot, q.message.chat_id)

async def show_main_menu(update):
    btns = get_keyboard_buttons()
    kb = []
    row = []
    for i,b in enumerate(btns):
        row.append(KeyboardButton(b['button_text']))
        if len(row)==2 or i==len(btns)-1: kb.append(row); row=[]
    if kb:
        await update.message.reply_text("⬇️ منو", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    else:
        await update.message.reply_text("⬇️ فایل بفرست", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("📁 ارسال فایل")]], resize_keyboard=True))

async def show_main_menu_msg(bot, cid):
    btns = get_keyboard_buttons()
    kb = []
    row = []
    for i,b in enumerate(btns):
        row.append(KeyboardButton(b['button_text']))
        if len(row)==2 or i==len(btns)-1: kb.append(row); row=[]
    await bot.send_message(cid, "⬇️ منو", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True) if kb else None)

async def handle_all(update, context):
    u = update.effective_user; m = update.message
    if not m: return
    if is_banned(u.id): await m.reply_text("⛔ بن"); return
    save_user(u)
    file = None; name = None; typ = None
    if m.document: file=m.document; name=file.file_name or f"doc_{file.file_unique_id}"; typ="سند"
    elif m.video: file=m.video; name=f"vid_{file.file_unique_id}.mp4"; typ="ویدیو"
    elif m.audio: file=m.audio; name=file.file_name or f"aud_{file.file_unique_id}.mp3"; typ="صوت"
    elif m.photo: file=m.photo[-1]; name=f"pic_{file.file_unique_id}.jpg"; typ="تصویر"
    elif m.voice: file=m.voice; name=f"voice_{file.file_unique_id}.ogg"; typ="ویس"
    else:
        txt = m.text
        if txt == "📁 ارسال فایل":
            await m.reply_text("📁 فایل را ارسال کنید")
        else:
            cm = get_custom_msg(txt)
            if cm: await m.reply_text(cm['response_text'])
            else: await m.reply_text("📁 فایل ارسال کن")
        return

    add_log(f"📁 {typ}: {name}")
    try:
        s = await m.reply_text("⏳ ...")
        fobj = await context.bot.get_file(file.file_id)
        os.makedirs(config.Config.UPLOAD_FOLDER, exist_ok=True)
        fpath = os.path.join(config.Config.UPLOAD_FOLDER, name)
        await fobj.download_to_drive(fpath)
        db = database.get_db()
        db.execute('INSERT INTO files (file_id,file_name,file_type,message_id,chat_id) VALUES (?,?,?,?,?)',
                   (file.file_id, name, typ, m.message_id, u.id))
        db.commit(); db.close()
        code = secrets.token_hex(4)
        save_link(code, file.file_id, name)
        global bot_username
        if not bot_username:
            me = await context.bot.get_me(); bot_username = me.username
        link = f"https://t.me/{bot_username}?start={code}"
        await s.edit_text(
            f"✅ ذخیره شد\n📄 `{name}`\n🔗 `{link}`",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔗 فایل", url=link)]])
        )
        add_log(f"✅ {name} -> {code}")
    except Exception as e:
        add_log(f"❌ {e}")
        await m.reply_text(f"❌ {str(e)[:200]}")

async def err(update, context):
    add_log(f"❌ {context.error}")

def run_bot():
    global application, stop_event, bot_username
    add_log("🚀 راه‌اندازی...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    stop_event.clear()

    async def start_app():
        global application, bot_username
        app = Application.builder().token(config.Config.BOT_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(check_join, pattern="^check_join$"))
        app.add_handler(MessageHandler(filters.ALL, handle_all))
        app.add_error_handler(err)
        application = app
        me = await app.bot.get_me(); bot_username = me.username
        add_log(f"✅ @{bot_username} آماده")
        await app.initialize(); await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        while not stop_event.is_set():
            await asyncio.sleep(1)
        add_log("🛑 توقف")
        await app.updater.stop(); await app.stop(); await app.shutdown()
        application = None

    try:
        loop.run_until_complete(start_app())
    except Exception as e:
        add_log(f"💀 {e}")
    finally:
        loop.close()
        add_log("⏹️ ربات متوقف")

def stop_bot():
    if application:
        add_log("سیگنال توقف")
        stop_event.set()
        return True
    return False