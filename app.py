from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
import config
import database
import os
import threading

app = Flask(__name__)
app.secret_key = 'khandaqh_panel_2026_secret_key'

bot_thread = None
bot_started = False

def start_bot():
    global bot_thread, bot_started
    if bot_started:
        stop_bot_instance()
    if config.Config.BOT_TOKEN:
        try:
            import bot
            bot_thread = threading.Thread(target=bot.run_bot, daemon=True)
            bot_thread.start()
            bot_started = True
            print("✅ ربات شروع شد")
        except Exception as e:
            print(f"❌ خطا: {e}")

def stop_bot_instance():
    global bot_started
    try:
        import bot
        if bot.stop_bot():
            bot_started = False
            print("✅ ربات متوقف شد")
            return True
    except Exception as e:
        print(f"❌ خطا در توقف ربات: {e}")
    return False

# ========== Routes ==========
@app.route('/')
def index():
    if not config.Config.is_configured():
        return redirect(url_for('setup_token'))
    return render_template('index.html')

@app.route('/setup/token', methods=['GET', 'POST'])
def setup_token():
    if request.method == 'POST':
        token = request.form.get('token', '').strip()
        if token:
            config.Config.BOT_TOKEN = token
            config.Config.save()
            return redirect(url_for('setup_path'))
    return render_template('setup_1_token.html')

@app.route('/setup/path', methods=['GET', 'POST'])
def setup_path():
    if request.method == 'POST':
        upload_path = request.form.get('upload_path', '').strip()
        if upload_path:
            try:
                upload_path = upload_path.replace('\\', '/').rstrip('/')
                os.makedirs(upload_path, exist_ok=True)
                test_file = os.path.join(upload_path, '.test_write')
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
                config.Config.UPLOAD_FOLDER = upload_path
                config.Config.save()
                database.init_db()
                start_bot()
                return redirect(url_for('index'))
            except Exception as e:
                return f"<h2>❌ خطا: {str(e)}</h2><a href='/setup/path'>برگشت</a>", 500
    return render_template('setup_2_path.html')

# ========== API Routes ==========
@app.route('/api/status')
def api_status():
    try:
        import bot
        logs = bot.log_messages[-100:] if hasattr(bot, 'log_messages') else []
        return jsonify({"status": "running" if bot_started else "stopped", "logs": logs})
    except:
        return jsonify({"status": "error", "logs": []})

@app.route('/api/bot/toggle', methods=['POST'])
def toggle_bot():
    global bot_started
    data = request.get_json()
    action = data.get('action')
    if action == 'start' and not bot_started:
        start_bot()
    elif action == 'stop' and bot_started:
        stop_bot_instance()
    return jsonify({"success": True, "running": bot_started})

@app.route('/api/settings', methods=['GET'])
def get_settings():
    return jsonify({
        "token": config.Config.BOT_TOKEN[-10:] if config.Config.BOT_TOKEN else "",
        "upload_folder": config.Config.UPLOAD_FOLDER
    })

@app.route('/api/settings/update', methods=['POST'])
def update_settings():
    data = request.get_json()
    new_token = data.get('token', '').strip()
    new_path = data.get('upload_folder', '').strip()
    if new_token:
        config.Config.BOT_TOKEN = new_token
    if new_path:
        try:
            os.makedirs(new_path, exist_ok=True)
            config.Config.UPLOAD_FOLDER = new_path
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    config.Config.save()
    # restart bot
    if bot_started:
        stop_bot_instance()
        threading.Timer(1.0, start_bot).start()
    return jsonify({"success": True})

@app.route('/api/logout', methods=['POST'])
def logout():
    global bot_started
    if bot_started:
        stop_bot_instance()
    if os.path.exists(config.CONFIG_FILE):
        os.remove(config.CONFIG_FILE)
    config.Config.BOT_TOKEN = None
    config.Config.UPLOAD_FOLDER = 'uploads'
    return jsonify({"success": True, "redirect": "/setup/token"})

@app.route('/api/messages', methods=['GET', 'POST', 'PUT', 'DELETE'])
def handle_messages():
    conn = database.get_db()
    try:
        if request.method == 'GET':
            msgs = conn.execute('SELECT * FROM custom_messages ORDER BY id DESC').fetchall()
            return jsonify([dict(m) for m in msgs])
        elif request.method == 'POST':
            data = request.get_json()
            command = data.get('command', '').strip()
            text = data.get('text', '').strip()
            if not command or not text:
                return jsonify({"error": "فیلدها خالی"}), 400
            conn.execute('INSERT OR REPLACE INTO custom_messages (command, response_text) VALUES (?,?)', (command, text))
            conn.commit()
            return jsonify({"success": True})
        elif request.method == 'PUT':
            data = request.get_json()
            conn.execute('UPDATE custom_messages SET command=?, response_text=? WHERE id=?',
                        (data['command'], data['text'], data['id']))
            conn.commit()
            return jsonify({"success": True})
        elif request.method == 'DELETE':
            msg_id = request.args.get('id')
            if msg_id:
                conn.execute('DELETE FROM custom_messages WHERE id=?', (msg_id,))
                conn.commit()
            return jsonify({"success": True})
    finally:
        conn.close()

@app.route('/api/files')
def api_files():
    conn = database.get_db()
    files = conn.execute('SELECT * FROM files ORDER BY upload_date DESC').fetchall()
    conn.close()
    return jsonify([dict(f) for f in files])

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(config.Config.UPLOAD_FOLDER, filename)

@app.route('/api/users')
def api_users():
    conn = database.get_db()
    users = conn.execute('SELECT * FROM users ORDER BY join_date DESC').fetchall()
    conn.close()
    return jsonify([dict(u) for u in users])

@app.route('/api/buttons', methods=['GET', 'POST', 'DELETE'])
def handle_buttons():
    conn = database.get_db()
    try:
        if request.method == 'GET':
            buttons = conn.execute('SELECT * FROM custom_buttons ORDER BY priority').fetchall()
            return jsonify([dict(b) for b in buttons])
        elif request.method == 'POST':
            data = request.get_json()
            conn.execute(
                'INSERT INTO custom_buttons (button_text, action_type, action_value, menu_type, parent_command, priority, requires_parent) VALUES (?,?,?,?,?,?,?)',
                (data.get('text'), data.get('action_type'), data.get('action_value'), data.get('menu_type', 'keyboard'), 'main', 0, 0)
            )
            conn.commit()
            return jsonify({"success": True})
        elif request.method == 'DELETE':
            b_id = request.args.get('id')
            conn.execute('DELETE FROM custom_buttons WHERE id=?', (b_id,))
            conn.commit()
            return jsonify({"success": True})
    finally:
        conn.close()

@app.route('/api/force_join', methods=['GET', 'POST', 'PUT', 'DELETE'])
def handle_force_join():
    conn = database.get_db()
    try:
        if request.method == 'GET':
            channels = conn.execute('SELECT * FROM force_join').fetchall()
            return jsonify([dict(c) for c in channels])
        elif request.method == 'POST':
            data = request.get_json()
            conn.execute('INSERT OR IGNORE INTO force_join (channel_name, channel_username, custom_message) VALUES (?,?,?)',
                        (data['name'], data['username'], data.get('message', '')))
            conn.commit()
            return jsonify({"success": True})
        elif request.method == 'PUT':
            data = request.get_json()
            conn.execute('UPDATE force_join SET enabled=? WHERE id=?', (data['enabled'], data['id']))
            conn.commit()
            return jsonify({"success": True})
        elif request.method == 'DELETE':
            ch_id = request.args.get('id')
            conn.execute('DELETE FROM force_join WHERE id=?', (ch_id,))
            conn.commit()
            return jsonify({"success": True})
    finally:
        conn.close()

@app.route('/api/bans', methods=['GET', 'POST', 'DELETE'])
def handle_bans():
    conn = database.get_db()
    try:
        if request.method == 'GET':
            bans = conn.execute('SELECT * FROM banned_users').fetchall()
            return jsonify([dict(b) for b in bans])
        elif request.method == 'POST':
            data = request.get_json()
            conn.execute('INSERT OR REPLACE INTO banned_users (user_id, first_name) VALUES (?,?)',
                        (data['user_id'], data.get('first_name', 'Unknown')))
            conn.commit()
            return jsonify({"success": True})
        elif request.method == 'DELETE':
            user_id = request.args.get('user_id')
            conn.execute('DELETE FROM banned_users WHERE user_id=?', (user_id,))
            conn.commit()
            return jsonify({"success": True})
    finally:
        conn.close()

if __name__ == '__main__':
    print("=" * 50)
    print("🤖 پنل مدیریت ربات تلگرام - نسخه 1.0 بتا")
    print("👨‍💻 توسعه‌دهنده: KhandaQh")
    print("📅 2026-2027")
    print("=" * 50)
    if config.Config.load():
        print("✅ تنظیمات قبلی بارگذاری شد")
        database.init_db()
        start_bot()
    app.run(debug=False, port=5000, use_reloader=False)