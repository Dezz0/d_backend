import os
import sys
import string
import random

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from app.models import Base
from app.auth import get_password_hash
from app.models import User

# ---------- Генерация случайных строк ----------
def generate_random_string(length=3):
    """Генерирует случайную строку из букв и цифр"""
    # chars = string.ascii_letters + string.digits
    # return ''.join(random.choice(chars) for _ in range(length))
    """Пароль для админа во время тестирования"""
    return 'admin'


ADMIN_LOGIN = "admin"
ADMIN_PASSWORD = generate_random_string()

DATABASE_URL = os.getenv("DATABASE_URL")

def init_database():
    # Используем URL из docker-compose
    engine = create_engine(DATABASE_URL)

    # Создаем таблицы
    Base.metadata.create_all(bind=engine)

    # Создаем сессию
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Проверяем, существует ли уже админ
        existing_admin = db.query(User).filter(User.login == ADMIN_LOGIN).first()
        if not existing_admin:
            # Создаем администратора
            admin_user = User(
                login=ADMIN_LOGIN,
                hashed_password=get_password_hash(ADMIN_PASSWORD),
                is_admin=True,
                application_submitted=False
            )
            db.add(admin_user)
            db.commit()
            print('=======================')
            print(f"Admin user created:")
            print(f"Login: {ADMIN_LOGIN}")
            print(f"Password: {ADMIN_PASSWORD}")
            print('=======================')
        else:
            print("Admin user already exists")

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    init_database()