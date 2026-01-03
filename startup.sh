#!/bin/bash

# Ждем пока база данных будет готова
echo "Waiting for database to be ready..."
sleep 10

# Инициализируем базу данных
python scripts/init_db.py

# Запускаем приложение
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload