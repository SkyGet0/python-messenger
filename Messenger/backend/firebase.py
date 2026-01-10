import os
import firebase_admin
from firebase_admin import credentials, db
from dotenv import load_dotenv
from pathlib import Path

# Загружаем .env из корня проекта
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

# Получаем путь к ключу и делаем его абсолютным
cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
db_url = os.getenv("FIREBASE_DB_URL")

# преобразуем путь к ключу в абсолютный
cred_path = str((Path(__file__).parent.parent / cred_path).resolve())

# Проверка инициализации
if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred, {
        'databaseURL': db_url
    })

__all__ = ['db']