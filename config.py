import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    PORT = int(os.getenv("PORT", 8080))
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///chatbot.db")
    DB_PATH = os.getenv("DB_PATH", "chatbot.db")

config = Config()
