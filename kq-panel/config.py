import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')

class Config:
    bots = []          # لیست دیکشنری‌های هر بات: {id, token, type, folder}
    current_bot_id = 1 # آیدی بات فعال
    BASE_URL = "http://127.0.0.1:5000"

    @classmethod
    def load(cls):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            cls.bots = data.get('bots', [])
            cls.current_bot_id = data.get('current', 1)
            cls.BASE_URL = data.get('base_url', cls.BASE_URL)
            return True
        return False

    @classmethod
    def save(cls):
        data = {
            'bots': cls.bots,
            'current': cls.current_bot_id,
            'base_url': cls.BASE_URL
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @classmethod
    def get_bot(cls, bot_id):
        for bot in cls.bots:
            if bot['id'] == bot_id:
                return bot
        return None

    @classmethod
    def add_bot(cls, token, bot_type):
        new_id = max([b['id'] for b in cls.bots] + [0]) + 1
        folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), f'uploads/bot_{new_id}')
        bot = {
            'id': new_id,
            'token': token,
            'type': bot_type,
            'folder': folder
        }
        cls.bots.append(bot)
        cls.save()
        return bot