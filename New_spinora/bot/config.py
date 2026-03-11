import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram Bot Token
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    
    # Storage path
    STORAGE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'storage.json')
    
    # Web App URL
    WEB_APP_URL = os.getenv('PUBLIC_WEBAPP_URL', 'http://localhost:3000')
    
    # Development mode
    DEV_AUTH_BYPASS = os.getenv('DEV_AUTH_BYPASS', '0') == '1'
    DEV_TELEGRAM_ID = os.getenv('DEV_TELEGRAM_ID', '123456789')
    DEV_USERNAME = os.getenv('DEV_USERNAME', 'testuser')
    DEV_FIRST_NAME = os.getenv('DEV_FIRST_NAME', 'Test')
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.BOT_TOKEN and not cls.DEV_AUTH_BYPASS:
            raise ValueError("BOT_TOKEN is required in production mode")
        return True