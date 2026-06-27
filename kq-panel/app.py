from flask import Flask, render_template, request, jsonify, redirect, url_for, session, g, send_from_directory
import config
import database
import bot
import os
import threading
import secrets
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'kq-panel-v2-secret-2026'

# -------- before request ----------
@app.before_request
def load_current_bot():
    bot_id = session.get('bot_id')
    if bot_id:
        g.current_bot = config.Config.get_bot(bot_id)
    else:
        g.current_bot = None

# -------- main page ----------
@app.route('/')
def index():
    if not config.Config.bots:
        return redirect('/setup/token')
    if not session.get('bot_id'):
        session['bot_id'] = config.Config.bots[0]['id']
    return render_template('index.html')

# -------- setup ----------
@app.route('/setup/token', methods=['GET', 'POST'])
def setup_token():
    if request.method == 'POST':
        token = request.form['token'].strip()
        session['new_token'] = token
        return redirect('/setup/type')
    return render_template('setup_token.html')

@app.route('/setup/type', methods=['GET', 'POST'])
def setup_type():
    if request.method == 'POST':
        bot_type = request.form['bot_type']
        session['new_type'] = bot_type
        if bot_type == 'assistant':
            return redirect('/setup/ai_token')
        else:
            return redirect('/setup/confirm')
    return render_template('setup_type.html')

@app.route('/setup/ai_token', methods=['GET', 'POST'])
def setup_ai_token():
    if request.method == 'POST':
        ai_token = request.form['ai_token'].strip()
        session['ai_token'] = ai_token
        return redirect('/setup/ai_model')
    return render_template('setup_ai_token.html')

@app.route('/setup/ai_model', methods=['GET', 'POST'])
def setup_ai_model():
    if request.method == 'POST':
        ai_model = request.form['ai_model']
        session['ai_model'] = ai_model
        return redirect('/setup/confirm')
    return render_template('setup_ai_model.html')

@app.route('/setup/confirm')
def setup_confirm():
    return render_template('setup_confirm.html',
                           token=session.get('new_token', ''),
                           bot_type=session.get('new_type', ''),
                           ai_token=session.get('ai_token', ''),
                           ai_model=session.get('ai_model', ''))

@app.route('/setup/final', methods=['POST'])
def setup_final():
    token = session.pop('new_token')
    bot_type = session.pop('new_type')
    ai_token = session.pop('ai_token', None)
    ai_model = session.pop('ai_model', None)

    new_bot = config.Config.add_bot(token, bot_type)
    base = os.path.dirname(os.path.abspath(__file__))
    if bot_type == 'uploader':
        folder = os.path.join(base, f'uploads/bot_{new_bot["id"]}')
    else:  # assistant
        folder = os.path.join(base, f'database/bot_{new_bot["id"]}')
    os.makedirs(folder, exist_ok=True)
    new_bot['folder'] = folder

    if bot_type == 'assistant':
        new_bot['ai_token'] = ai_token
        new_bot['ai_model'] = ai_model
        new_bot['ai_commands'] = []
        new_bot['ai_forbidden'] = []
        new_bot['ai_dnd'] = {
            'enabled': False,
            'message': 'سلام فعلاً امکان پاسخ‌گویی ندارم. با تشکر از صبوری شما.',
            'timer_enabled': False,
            'start_time': '',
            'end_time': '',
            'start_date': '',
            'end_date': ''
        }

    config.Config.save()
    database.init_db()
    bot.start_bot(new_bot['id'])
    session['bot_id'] = new_bot['id']
    return redirect('/')

# -------- Bot management APIs ----------
@app.route('/api/bots')
def list_bots():
    return jsonify(config.Config.bots)

@app.route('/api/switch_bot', methods=['POST'])
def switch_bot():
    data = request.get_json()
    session['bot_id'] = data['bot_id']
    return jsonify(success=True)

@app.route('/api/add_bot', methods=['POST'])
def add_bot():
    data = request.get_json()
    token = data['token']
    bot_type = data['type']
    # فقط آپلودر و دستیار مجاز هستند
    if bot_type not in ['uploader', 'assistant']:
        return jsonify(success=False, error='نوع ربات نامعتبر یا در دسترس نیست.')
    new_bot = config.Config.add_bot(token, bot_type)
    base = os.path.dirname(os.path.abspath(__file__))
    if bot_type == 'uploader':
        folder = os.path.join(base, f'uploads/bot_{new_bot["id"]}')
    else:
        folder = os.path.join(base, f'database/bot_{new_bot["id"]}')
    os.makedirs(folder, exist_ok=True)
    new_bot['folder'] = folder

    if bot_type == 'assistant':
        new_bot['ai_token'] = data.get('ai_token', '')
        new_bot['ai_model'] = data.get('ai_model', 'gpt-3.5-turbo')
        new_bot['ai_commands'] = []
        new_bot['ai_forbidden'] = []
        new_bot['ai_dnd'] = {
            'enabled': False,
            'message': 'سلام فعلاً امکان پاسخ‌گویی ندارم. با تشکر از صبوری شما.',
            'timer_enabled': False,
            'start_time': '',
            'end_time': '',
            'start_date': '',
            'end_date': ''
        }
    config.Config.save()
    bot.start_bot(new_bot['id'])
    return jsonify(success=True, bot=new_bot)

@app.route('/api/current_bot')
def current_bot():
    if g.current_bot:
        return jsonify(g.current_bot)
    return jsonify({})

def get_bot_id():
    return g.current_bot['id'] if g.current_bot else None

# -------- Common APIs (status, messages, files, users, buttons, force_join, bans, broadcast, settings) ----------
@app.route('/api/status')
def api_status():
    bot_id = get_bot_id()
    if not bot_id:
        return jsonify(status='no_bot', logs=[])
    running = bot_id in bot.active_bots
    return jsonify(status='running' if running else 'stopped', logs=bot.log_messages[-50:])

@app.route('/api/toggle', methods=['POST'])
def toggle():
    bot_id = get_bot_id()
    act = request.json['action']
    if act == 'start':
        bot.start_bot(bot_id)
    elif act == 'stop':
        bot.stop_bot(bot_id)
    return jsonify(success=True, running=(bot_id in bot.active_bots))

@app.route('/api/messages', methods=['GET','POST','PUT','DELETE'])
def messages():
    db = database.get_db()
    bot_id = get_bot_id()
    if request.method == 'GET':
        rows = db.execute('SELECT * FROM custom_messages WHERE bot_id=?', (bot_id,)).fetchall()
        return jsonify([dict(r) for r in rows])
    elif request.method == 'POST':
        d = request.json
        db.execute('INSERT OR REPLACE INTO custom_messages (bot_id, command, response_text) VALUES (?,?,?)',
                   (bot_id, d['command'], d['text']))
        db.commit()
        return jsonify(success=True)
    elif request.method == 'PUT':
        d = request.json
        db.execute('UPDATE custom_messages SET command=?, response_text=? WHERE id=? AND bot_id=?',
                   (d['command'], d['text'], d['id'], bot_id))
        db.commit()
        return jsonify(success=True)
    elif request.method == 'DELETE':
        db.execute('DELETE FROM custom_messages WHERE id=? AND bot_id=?', (request.args['id'], bot_id))
        db.commit()
        return jsonify(success=True)

@app.route('/api/files')
def files():
    db = database.get_db()
    rows = db.execute('SELECT * FROM files WHERE bot_id=? ORDER BY upload_date DESC', (get_bot_id(),)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    bot = g.current_bot
    if not bot:
        return "ربات مشخص نیست", 404
    return send_from_directory(bot['folder'], filename)

@app.route('/api/users')
def users():
    db = database.get_db()
    rows = db.execute('SELECT * FROM users WHERE bot_id=? ORDER BY join_date DESC', (get_bot_id(),)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/buttons', methods=['GET','POST','DELETE'])
def buttons():
    db = database.get_db()
    bot_id = get_bot_id()
    if request.method == 'GET':
        rows = db.execute('SELECT * FROM custom_buttons WHERE bot_id=?', (bot_id,)).fetchall()
        return jsonify([dict(r) for r in rows])
    elif request.method == 'POST':
        d = request.json
        db.execute('INSERT INTO custom_buttons (bot_id, button_text, action_type, action_value, menu_type) VALUES (?,?,?,?,?)',
                   (bot_id, d['text'], d['action_type'], d['action_value'], d.get('menu_type','keyboard')))
        db.commit()
        return jsonify(success=True)
    elif request.method == 'DELETE':
        db.execute('DELETE FROM custom_buttons WHERE id=? AND bot_id=?', (request.args['id'], bot_id))
        db.commit()
        return jsonify(success=True)

@app.route('/api/force_join', methods=['GET','POST','PUT','DELETE'])
def force_join():
    db = database.get_db()
    bot_id = get_bot_id()
    if request.method == 'GET':
        rows = db.execute('SELECT * FROM force_join WHERE bot_id=?', (bot_id,)).fetchall()
        return jsonify([dict(r) for r in rows])
    elif request.method == 'POST':
        d = request.json
        db.execute('INSERT OR IGNORE INTO force_join (bot_id, channel_name, channel_username, custom_message) VALUES (?,?,?,?)',
                   (bot_id, d['name'], d['username'], d.get('message','')))
        db.commit()
        return jsonify(success=True)
    elif request.method == 'PUT':
        d = request.json
        db.execute('UPDATE force_join SET enabled=? WHERE id=? AND bot_id=?', (d['enabled'], d['id'], bot_id))
        db.commit()
        return jsonify(success=True)
    elif request.method == 'DELETE':
        db.execute('DELETE FROM force_join WHERE id=? AND bot_id=?', (request.args['id'], bot_id))
        db.commit()
        return jsonify(success=True)

@app.route('/api/bans', methods=['GET','POST','DELETE'])
def bans():
    db = database.get_db()
    bot_id = get_bot_id()
    if request.method == 'GET':
        rows = db.execute('SELECT * FROM banned_users WHERE bot_id=?', (bot_id,)).fetchall()
        return jsonify([dict(r) for r in rows])
    elif request.method == 'POST':
        d = request.json
        db.execute('INSERT OR REPLACE INTO banned_users (user_id, first_name, bot_id) VALUES (?,?,?)',
                   (d['user_id'], d.get('first_name','Unknown'), bot_id))
        db.commit()
        return jsonify(success=True)
    elif request.method == 'DELETE':
        db.execute('DELETE FROM banned_users WHERE user_id=? AND bot_id=?', (request.args['user_id'], bot_id))
        db.commit()
        return jsonify(success=True)

@app.route('/api/broadcast', methods=['POST'])
def broadcast():
    d = request.json
    text = d['message']
    schedule = d.get('scheduled_time')
    tz = d.get('timezone')
    bot_id = get_bot_id()
    db = database.get_db()
    db.execute('INSERT INTO broadcast_jobs (bot_id, message_text, scheduled_time, timezone) VALUES (?,?,?,?)',
               (bot_id, text, schedule, tz))
    db.commit()
    return jsonify(success=True, message='پیام همگانی ثبت شد.')

@app.route('/api/settings', methods=['GET'])
def settings():
    bot = g.current_bot
    if not bot:
        return jsonify({})
    return jsonify(token=bot['token'][-10:], folder=bot['folder'])

@app.route('/api/settings/update', methods=['POST'])
def update_settings():
    d = request.json
    bot = g.current_bot
    if not bot:
        return jsonify(success=False)
    if d.get('token'):
        bot['token'] = d['token']
    if d.get('folder'):
        bot['folder'] = d['folder']
        os.makedirs(d['folder'], exist_ok=True)
    config.Config.save()
    if bot['id'] in bot.active_bots:
        bot.stop_bot(bot['id'])
        threading.Timer(1, bot.start_bot, args=(bot['id'],)).start()
    return jsonify(success=True)

@app.route('/api/logout', methods=['POST'])
def logout():
    for b in config.Config.bots:
        bot.stop_bot(b['id'])
    config.Config.bots = []
    config.Config.save()
    session.clear()
    return jsonify(success=True, redirect='/setup/token')

# -------- AI specific APIs ----------
@app.route('/api/ai/commands', methods=['GET', 'POST', 'DELETE'])
def ai_commands():
    bot = g.current_bot
    if not bot or bot['type'] != 'assistant':
        return jsonify(error='دسترسی غیرمجاز'), 403
    if request.method == 'GET':
        return jsonify(bot.get('ai_commands', []))
    elif request.method == 'POST':
        data = request.json
        text = data.get('text', '').strip()
        if not text:
            return jsonify(error='متن خالی'), 400
        bot.setdefault('ai_commands', []).append({'id': secrets.token_hex(8), 'text': text, 'enabled': True})
        config.Config.save()
        return jsonify(success=True)
    elif request.method == 'DELETE':
        cmd_id = request.args.get('id')
        bot['ai_commands'] = [c for c in bot['ai_commands'] if c['id'] != cmd_id]
        config.Config.save()
        return jsonify(success=True)

@app.route('/api/ai/commands/toggle', methods=['POST'])
def ai_command_toggle():
    bot = g.current_bot
    data = request.json
    cmd_id = data['id']
    for cmd in bot['ai_commands']:
        if cmd['id'] == cmd_id:
            cmd['enabled'] = not cmd['enabled']
            break
    config.Config.save()
    return jsonify(success=True)

@app.route('/api/ai/forbidden', methods=['GET', 'POST', 'DELETE'])
def ai_forbidden():
    bot = g.current_bot
    if not bot or bot['type'] != 'assistant':
        return jsonify(error='دسترسی غیرمجاز'), 403
    if request.method == 'GET':
        return jsonify(bot.get('ai_forbidden', []))
    elif request.method == 'POST':
        data = request.json
        phrase = data.get('phrase', '').strip()
        response = data.get('response', '').strip()
        if not phrase:
            return jsonify(error='عبارت خالی'), 400
        bot.setdefault('ai_forbidden', []).append({
            'id': secrets.token_hex(8),
            'phrase': phrase,
            'response': response or 'ببخشید اجازه پردازش این درخواست رو ندارم.',
            'enabled': True
        })
        config.Config.save()
        return jsonify(success=True)
    elif request.method == 'DELETE':
        fid = request.args.get('id')
        bot['ai_forbidden'] = [f for f in bot['ai_forbidden'] if f['id'] != fid]
        config.Config.save()
        return jsonify(success=True)

@app.route('/api/ai/forbidden/toggle', methods=['POST'])
def ai_forbidden_toggle():
    bot = g.current_bot
    data = request.json
    fid = data.get('id')
    if fid:
        # single toggle
        for item in bot['ai_forbidden']:
            if item['id'] == fid:
                item['enabled'] = not item['enabled']
                break
    else:
        # global toggle: invert all
        new_state = not all(item.get('enabled', True) for item in bot.get('ai_forbidden', []))
        for item in bot.get('ai_forbidden', []):
            item['enabled'] = new_state
    config.Config.save()
    return jsonify(success=True)

@app.route('/api/ai/dnd', methods=['GET', 'POST'])
def ai_dnd():
    bot = g.current_bot
    if not bot or bot['type'] != 'assistant':
        return jsonify(error='دسترسی غیرمجاز'), 403
    if request.method == 'GET':
        return jsonify(bot.get('ai_dnd', {}))
    elif request.method == 'POST':
        data = request.json
        bot['ai_dnd'] = data
        config.Config.save()
        return jsonify(success=True)

@app.route('/api/ai/settings', methods=['GET', 'POST'])
def ai_settings():
    bot = g.current_bot
    if not bot or bot['type'] != 'assistant':
        return jsonify(error='دسترسی غیرمجاز'), 403
    if request.method == 'GET':
        return jsonify({
            'ai_token': bot.get('ai_token', ''),
            'ai_model': bot.get('ai_model', '')
        })
    elif request.method == 'POST':
        data = request.json
        if 'ai_token' in data:
            bot['ai_token'] = data['ai_token']
        if 'ai_model' in data:
            bot['ai_model'] = data['ai_model']
        config.Config.save()
        return jsonify(success=True)

# -------- run ----------
if __name__ == '__main__':
    config.Config.load()
    database.init_db()
    for b in config.Config.bots:
        bot.start_bot(b['id'])
    app.run(debug=False, port=5000, use_reloader=False)