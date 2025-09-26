# Использование официального образа Python 3.10
FROM python:3.10-slim

# Установка переменных окружения для корректной работы
ENV PYTHONUNBUFFERED 1
ENV TZ=Europe/Moscow

# Создание рабочей директории в контейнере
WORKDIR /app

# Копирование требований и их установка
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Копирование всего кода
COPY . /app

# Команда для запуска бота
CMD ["python", "FootballPostBot.py"]