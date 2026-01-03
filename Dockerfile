# Используем официальный Python-образ
FROM python:3.11

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы зависимостей
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем нужный код в контейнер
COPY ./app ./app
COPY ./scripts ./scripts

# Создаем скрипт запуска
COPY startup.sh .
RUN chmod +x startup.sh

# Указываем команду запуска приложения
CMD ["./startup.sh"]