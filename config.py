import json
import os

CONFIG_FILE = 'config.json'

class Config:
    BOT_TOKEN = None
    UPLOAD_FOLDER = 'uploads'
    BASE_URL = "http://127.0.0.1:5000"
    
    @classmethod
    def save(cls):
        """ذخیره تنظیمات در فایل JSON"""
        data = {
            'bot_token': cls.BOT_TOKEN,
            'upload_folder': cls.UPLOAD_FOLDER,
            'base_url': cls.BASE_URL
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print("💾 تنظیمات ذخیره شد")
    
    @classmethod
    def load(cls):
        """بارگذاری تنظیمات از فایل JSON"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                cls.BOT_TOKEN = data.get('bot_token')
                cls.UPLOAD_FOLDER = data.get('upload_folder', 'uploads')
                cls.BASE_URL = data.get('base_url', 'http://127.0.0.1:5000')
                print("📂 تنظیمات قبلی بارگذاری شد")
                return True
            except:
                print("⚠️ خطا در بارگذاری تنظیمات")
        return False
    
    @classmethod
    def is_configured(cls):
        return cls.BOT_TOKEN is not None