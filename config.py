"""
Конфигурация бота
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN", "your-telegram-token")

# OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-openai-key")

# Database URL (SQLite для MVP, легко заменить на PostgreSQL)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./lovebot.db")

# Настройки бота
MAX_SESSION_LIFETIME_HOURS = 24
FREE_REPORT_LIMIT = 500  # количество символов в бесплатном отчёте

# ID создателей (для тестовых функций)
ADMIN_IDS = [7490061524]  # Твой Telegram ID
