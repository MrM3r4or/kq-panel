from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
import config, database, os, threading

app = Flask(__name__)
app.secret_key = 'kq_panel_2026'
bot_thread = None
bot_started = False

def start_bot():
    global bot_thread, bot_started
    if bot_started: stop_bot()
    try:
        import bot
        bot_thread = threading.Thread(target=bot.run_bot, daemon=True)
        bot_thread.start()
        bot_started = True
        print("✅ ربات شروع")
    except Exception as e: print(f"❌ {e}")

def stop_bot():
    global bot_started
    try:
        import bot
        if bot.stop_bot(): bot_started = False
    except: pass

@app.route('/')
def index():
    if not config.Config.is_configured(): return redirect('/setup/token')
    return render_template('index.html')

@app.route('/setup/token', methods=['GET','POST'])
def setup_token():
    if request.method == 'POST':
        t = request.form['token'].strip()
        if t: config.Config.BOT_TOKEN = t; config.Config.save(); return redirect('/setup/path')
    return render_template('setup_1_token.html')

@app.route('/setup/path', methods=['GET','POST'])
def setup_path():
    if request.method == 'POST':
        p = request.form['upload_path'].strip().replace('\\','/')
        try:
            os.makedirs(p, exist_ok=True)
            open(os.path.join(p,'.test'),'w').close(); os.remove(os.path.join(p,'.test'))
            config.Config.UPLOAD_FOLDER = p; config.Config.save(); database.init_db(); start_bot()
            return redirect('/')
        except Exception as e:
            return f"<h2>خطا: {e}</h2><a href='/setup/path'>برگشت</a>", 500
    return render_template('setup_2_path.html')

@app.route('/api/status')
def api_status():
    try:
        import bot
        return jsonify({"status":"running" if bot_started else "stopped", "logs": bot.log_messages[-100:]})
    except:
        return jsonify({"status":"error","logs":[]})

@app.route('/api/bot/toggle', methods=['POST'])
def toggle():
    global bot_started
    act = request.get_json().get('action')
    if act == 'start': start_bot()
    elif act == 'stop': stop_bot()
    return jsonify(success=True, running=bot_started)

@app.route('/api/settings')
def settings():
    return jsonify(token=config.Config.BOT_TOKEN[-10:] if config.Config.BOT_TOKEN else "", upload_folder=config.Config.UPLOAD_FOLDER)

@app.route('/api/settings/update', methods=['POST'])
def update_settings():
    data = request.get_json()
    nt = data.get('token','').strip(); np = data.get('upload_folder','').strip()
    if nt: config.Config.BOT_TOKEN = nt
    if np:
        try:
            os.makedirs(np, exist_ok=True); config.Config.UPLOAD_FOLDER = np
        except Exception as e: return jsonify(success=False, error=str(e))
    config.Config.save()
    if bot_started: stop_bot(); threading.Timer(1, start_bot).start()
    return jsonify(success=True)

@app.route('/api/logout', methods=['POST'])
def logout():
    if bot_started: stop_bot()
    if os.path.exists(config.CONFIG_FILE): os.remove(config.CONFIG_FILE)
    config.Config.BOT_TOKEN = None; config.Config.UPLOAD_FOLDER = 'uploads'
    return jsonify(success=True, redirect='/setup/token')

# سایر APIها (messages, files, users, buttons, force_join, bans) مشابه قبل هستند
# ... (برای خلاصه شدن در اینجا نیاوردم، اما تو فایل کامل قبلی هستند)

if __name__ == '__main__':
    print("🤖 kQ Panel v1.0 Beta"); config.Config.load(); database.init_db()
    if config.Config.BOT_TOKEN: start_bot()
    app.run(debug=False, port=5000, use_reloader=False)