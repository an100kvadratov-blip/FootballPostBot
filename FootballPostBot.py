# -*- coding: utf-8 -*-
import telebot
import requests
import time
import logging
import os
import re
import pytz
from dotenv import load_dotenv
from datetime import datetime, timedelta

# --- 1. ЗАГРУЗКА ПЕРЕМЕННЫХ ИЗ .ENV ---
load_dotenv()

# --- 2. КОНСТАНТЫ API И TELEGRAM ---
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHANNEL_ID = os.getenv("TG_CHANNEL_ID")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

# Файл для хранения ключей (защита от дублирования)
POSTED_FILE = "posted_headlines_keys.txt"
NEWS_API_URL = "https://newsapi.org/v2/everything"

# --- КОНСТАНТЫ ЧАСОВОГО ПОЯСА И РАСПИСАНИЯ ---
TIMEZONE_MSK = pytz.timezone('Europe/Moscow')
START_HOUR = 8  # 08:00 МСК
END_HOUR = 23  # 23:00 МСК (бот останавливается после 22:59)

# Расписание: [1 пост/час, 2 поста/час]
POSTING_SCHEDULE = [
    [5],
    [25, 50]
]

# --- СТОП-СЛОВА ДЛЯ НОРМАЛИЗАЦИИ ЗАГОЛОВКОВ ---
RUSSIAN_STOP_WORDS = [
    'и', 'в', 'на', 'с', 'к', 'по', 'для', 'от', 'до', 'из', 'за', 'под', 'над', 'о', 'об',
    'у', 'а', 'но', 'или', 'что', 'как', 'это', 'при', 'после', 'его', 'ее', 'их',
    'они', 'мы', 'вы', 'ты', 'мне', 'тебе', 'себе', 'также', 'тоже', 'того', 'такого',
    'хотя', 'если', 'когда', 'где', 'куда', 'откуда', 'зачем', 'почему', 'который',
    'свой', 'своего', 'своих', 'своем', 'только', 'лишь', 'однако', 'впрочем',
    'вообще', 'например', 'даже', 'же', 'то', 'будет', 'был', 'была', 'было',
    'были', 'быть', 'есть', 'нас', 'вас', 'им', 'ей', 'нем', 'ней', 'него', 'нее',
    'ними', 'нему', 'нему', 'чем', 'чем', 'тем', 'еще', 'уже', 'все', 'всем', 'всю',
    'оба', 'обе', 'их', 'всех', 'каждый', 'любой', 'самый', 'более', 'менее', 'прямо', 'вдруг',
    'говорит', 'заявил', 'сказал', 'считает', 'рассказал', 'о том', 'что дал'
]

# --- ФИЛЬТРЫ ---

EUROPEAN_CLUBS = [
    "Реал", "Барселона", "Бавария", "ПСЖ", "Манчестер Сити", "Манчестер Юнайтед",
    "Ливерпуль", "Челси", "Арсенал", "Тоттенхэм", "Ювентус", "Милан", "Интер",
    "Наполи", "Боруссия Дортмунд", "Атлетико", "Порту", "Бенфика", "Аякс"
]

MUST_HAVE_KEYWORDS_API = [
                             "Чемпионов", "УЕФА", "Европа Лига", "Премьер-лига", "АПЛ",
                             "Ла Лига", "Серия А", "Бундеслига", "Лига 1", "Евро", "Кубок Мира",
                             "Месси", "Роналду", "Холанд", "Мбаппе", "Кейн", "Беллингем", "Салах", "Де Брюйне",
                             "Левандовски", "Гвардиола", "Клопп", "Винисиус", "Бензема",
                             "Травма", "Уволен", "Перешел", "Сделка", "Подписал", "Уйдет"
                         ] + EUROPEAN_CLUBS

MUST_HAVE_KEYWORDS_RU = [
    "футбол", "лига чемпионов", "апл", "чемпионат", "серия а", "бундеслига",
    "ла лига", "тренер", "матч", "гол", "пенальти", "кубок", "чемпион",
    "лига европы", "бомбардир", "плей-офф", "сборная",
    "Месси", "Роналду", "Реал", "Барселона", "Бавария", "ПСЖ", "Ливерпуль",
    "Челси", "Арсенал", "Ювентус", "Манчестер Юнайтед", "Манчестер Сити"
]

MUST_NOT_HAVE_KEYWORDS_RU = [
    "киберспорт", "Counter-Strike", "Dota 2", "EPL S2", "SINNERS", "FORZE", "Veroja",
    "Esports World Cup", "турнир", "Pavaga", "команда", "киберспортивный",
    "лада", "кубок гагарина", "континентальная хоккейная лига", "хоккейная",
    "хоккей", "шахматы", "фигурный", "теннис", "баскетбол", "гольф", "биатлон",
    "автоваз", "автомобиль", "ваз", "нива", "muras", "kyrgyzstan", "кыргызстан", "нхл",
    "кхл", "авангард", "трактор", "ак барс", "металлург", "спартак москва",
    "комбинезон", "шумахера", "израиль", "израиля", "израильские", "израильский", "израильской",
    "захарова", "политика", "санкции", "крипто", "инвестиции", "доллар",
    "курс валют", "госдума", "выборы", "украина", "израиль", "израильские",
    "двойные стандарты", "кремль", "государственный", "вшэ", "росреестра",
    "борис авакян", "республику сербскую", "вертолеты", "вертолеты россии", "яна рудковская",
    "верховный суд", "суд рф", "прокурор", "прокуратура", "судья",
    "финансист",
    "репарационный займ",
    "тэс",
    "трансляция", "смотреть", "онлайн", "прямой эфир", "vk видео", "матч тв",
    "перенесенный матч", "1-го тура",
    "РПЛ", "российская премьер", "Зенит", "ЦСКА", "Спартак", "Динамо", "Локомотив",
    "Краснодар", "Крылья Советов", "Ростов", "Рубин", "Ахмат", "Урал", "Факел",
    "Оренбург", "Сочи", "Нижний Новгород", "Химки", "Арсенал Тула",
    "Чемпионат России", "Кубок России", "Сборная России", "РФС", "России",
    "клещев", "уткин", "черданцев", "картавый футбол", "широков", "бубнов",
    "кавазашвили", "лошаков", "генич", "невский", "слуцкий", "орлов", "канделаки",
    "матвей сафонов высказался",
    "Турции", "Китай", "Японии", "Канада", "ОАЭ", "Мексика", "Австралия", "Бахрейн",
    "женский", "женская", "НБА", "НФЛ", "Регби", "Формула", "Крикет",
    "школьное питание", "школьное",
]

EXCLUDE_SOURCES = ["Mail.Ru", "Meduza.ru", "Tass.ru"]

# --- ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ И НАСТРОЙКА ЛОГИРОВАНИЯ ---
posted_headlines = set()


def setup_logging():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info("Настройка логирования завершена.")


def get_headline_key(headline):
    text = re.sub(r'[^\w\s]', '', headline.lower())
    words = text.split()
    significant_words = [word for word in words if word not in RUSSIAN_STOP_WORDS]
    significant_words.sort()
    return " ".join(significant_words)


def load_posted_headlines():
    global posted_headlines
    if os.path.exists(POSTED_FILE):
        try:
            with open(POSTED_FILE, 'r', encoding='utf-8') as f:
                posted_headlines = set(line.strip() for line in f if line.strip())
            logging.info(f"Загружено {len(posted_headlines)} ранее опубликованных ключей заголовков.")
        except Exception as e:
            logging.error(f"Ошибка при загрузке ключей из файла {POSTED_FILE}: {e}")


def save_posted_headline(headline_key):
    global posted_headlines
    posted_headlines.add(headline_key)
    try:
        with open(POSTED_FILE, 'a', encoding='utf-8') as f:
            f.write(headline_key + '\n')
    except Exception as e:
        logging.error(f"Ошибка при сохранении ключа в файл {POSTED_FILE}: {e}")


def escape_markdown_v2(text):
    """Экранирует символы для MarkdownV2."""
    special_chars = ['\\', '_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+',
                     '-', '=', '|', '{', '}', '.', '!', ':', "'", ',', '?', '/']
    text = text.replace('\\', '\\\\')
    for char in special_chars:
        if char != '\\':
            text = text.replace(char, f'\\{char}')
    return text


def clean_description(description):
    """
    Удаление нежелательных фраз в конце описания (например, "Читать далее…").
    """
    if not description:
        return ""

    unwanted_tail_patterns = [
        r'(\.\s*)*\s*(читайте|читать|подробнее|смотрите|далее|на\s*[^\s]+)\s*(\s*\.\s*)*\s*$',
        r'\s*\[\s*\]\s*$',
        r'(\s*\.\s*)*\s*$',
        r'\s*Ес\s*$'
    ]

    cleaned_description = description
    for pattern in unwanted_tail_patterns:
        cleaned_description = re.sub(pattern, '', cleaned_description, flags=re.IGNORECASE).strip()

    if cleaned_description and cleaned_description[-1] not in ('.', '!', '?', '"'):
        cleaned_description += "."

    return cleaned_description


def is_relevant(article_title, article_description, source_name, log_ignore=True):
    """Проверка на соответствие фильтрам MUST_NOT_HAVE и MUST_HAVE."""

    if log_ignore:
        logging.info(f"Проверка поста. Источник: {source_name}. Заголовок: '{article_title}'")

    full_text_lower = (article_title + " " + (article_description or "")).lower()

    for keyword in MUST_NOT_HAVE_KEYWORDS_RU:
        if keyword.lower() in full_text_lower:
            if log_ignore:
                logging.info(f"ИГНОР (ФИЛЬТР - {keyword}): '{article_title}'")
            return False

    found_must_have = any(keyword.lower() in full_text_lower for keyword in MUST_HAVE_KEYWORDS_RU)

    if found_must_have:
        if log_ignore:
            logging.info(f"ПРИНЯТА (Прошла оба фильтра): '{article_title}'")
        return True
    else:
        if log_ignore:
            logging.info(f"ИГНОР (НЕТ ФУТБОЛЬНЫХ КЛЮЧЕВЫХ СЛОВ): '{article_title}'")
        return False


def fetch_news_from_api():
    """Получает новости с NewsAPI."""

    if not NEWS_API_KEY:
        logging.error("NEWS_API_KEY не установлен. Проверьте .env файл.")
        return []

    from_time = (datetime.now(TIMEZONE_MSK) - timedelta(hours=10)).isoformat()

    q_filter = " OR ".join([f'"{k}"' for k in MUST_HAVE_KEYWORDS_API])

    params = {
        'qInTitle': q_filter,
        'language': 'ru',
        'sortBy': 'publishedAt',
        'apiKey': NEWS_API_KEY,
        'pageSize': 100,
        'from': from_time
    }

    try:
        response = requests.get(NEWS_API_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        logging.info(f"Получено {data.get('totalResults', 0)} потенциальных статей с NewsAPI.")
        return data.get('articles', [])
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка при запросе к NewsAPI: {e}")
        return []
    except Exception as e:
        logging.error(f"Неизвестная ошибка при обработке API: {e}")
        return []


def send_content_to_tg(bot_instance, title_ru, description_ru, image_url):
    """Отправляет сообщение в Telegram-канал."""

    if not TG_CHANNEL_ID:
        logging.error("TG_CHANNEL_ID не установлен. Публикация невозможна.")
        return

    safe_title = escape_markdown_v2(title_ru)
    safe_description = escape_markdown_v2(description_ru)

    final_text = f"⚽️ **{safe_title}**\n\n{safe_description}"

    try:
        bot_instance.send_photo(
            TG_CHANNEL_ID,
            photo=image_url,
            caption=final_text,
            parse_mode='MarkdownV2'
        )

        logging.info(f"УСПЕШНО ОПУБЛИКОВАНО (С ФОТО): {title_ru}")

    except telebot.apihelper.ApiTelegramException as e:
        logging.error(f"Ошибка Telegram API при публикации: {e}. Пропуск поста.")
    except Exception as e:
        logging.critical(f"Критическая ошибка при отправке в Telegram: {e}")


def get_next_post_time(current_time_msk):
    """
    Вычисляет следующее запланированное время поста (datetime object в МСК)
    согласно рабочему времени (08:00 - 23:00) и циклическому графику.
    """

    if current_time_msk.hour >= END_HOUR or current_time_msk.hour < START_HOUR:
        next_day = current_time_msk.date() + timedelta(days=1)
        next_post_time = TIMEZONE_MSK.localize(
            datetime(next_day.year, next_day.month, next_day.day, START_HOUR, POSTING_SCHEDULE[0][0])
        )
        return next_post_time

    for hour_delta in range(25):
        target_time = current_time_msk + timedelta(hours=hour_delta)
        target_time = target_time.replace(second=0, microsecond=0)

        current_hour_in_cycle = target_time.hour
        if current_hour_in_cycle < START_HOUR or current_hour_in_cycle >= END_HOUR:
            if hour_delta == 0:
                continue
            else:
                next_day = current_time_msk.date() + timedelta(days=1)
                next_post_time = TIMEZONE_MSK.localize(
                    datetime(next_day.year, next_day.month, next_day.day, START_HOUR, POSTING_SCHEDULE[0][0])
                )
                return next_post_time

        hour_in_cycle = (target_time.hour - START_HOUR) % 2
        schedule_for_hour = POSTING_SCHEDULE[hour_in_cycle]

        for minute in schedule_for_hour:
            candidate = target_time.replace(minute=minute)

            if candidate > current_time_msk:
                return candidate


def get_best_article_to_post(articles):
    """
    Фильтрует статьи на релевантность и дубликаты, возвращая самую новую (best)
    из подходящих статей.
    """
    best_article = None
    newest_timestamp = None
    excluded_sources_lower = [s.lower() for s in EXCLUDE_SOURCES]

    for article in articles:
        title_ru = article.get('title')
        description_ru = article.get('description')
        image_url = article.get('urlToImage')
        source_name = article.get('source', {}).get('name')
        published_at_str = article.get('publishedAt')

        if not title_ru or not image_url or not published_at_str:
            continue

        if source_name and source_name.lower() in excluded_sources_lower:
            continue

        headline_key = get_headline_key(title_ru)
        if headline_key in posted_headlines:
            continue

        if not is_relevant(title_ru, description_ru, source_name, log_ignore=False):
            continue

        try:
            published_time = datetime.fromisoformat(published_at_str.replace('Z', '+00:00')).astimezone(pytz.utc)
        except ValueError:
            logging.warning(f"Не удалось распарсить время для статьи: {title_ru}")
            continue

        if newest_timestamp is None or published_time > newest_timestamp:
            newest_timestamp = published_time
            best_article = article

    if best_article:
        logging.info(
            f"НАЙДЕНА ЛУЧШАЯ СТАТЬЯ: '{best_article.get('title')}' от {newest_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")

    return best_article


# --- ГЛАВНЫЙ ЦИКЛ БОТА ---

def main():
    setup_logging()

    if not TG_TOKEN or not TG_CHANNEL_ID or not NEWS_API_KEY:
        logging.critical("Критические переменные не установлены в .env.")
        return

    bot = telebot.TeleBot(TG_TOKEN)
    load_posted_headlines()

    logging.info("Бот запущен. Начинаю работу по расписанию (08:00 - 23:00 МСК)...")

    while True:
        try:
            current_time_msk = datetime.now(TIMEZONE_MSK)
            next_post_time = get_next_post_time(current_time_msk)

            sleep_duration = (next_post_time - current_time_msk).total_seconds()

            logging.info(f"Текущее время (МСК): {current_time_msk.strftime('%H:%M:%S')}")
            logging.info(f"Следующий пост запланирован на: {next_post_time.strftime('%Y-%m-%d %H:%M:%S')}")

            if sleep_duration > 0:
                logging.info(f"Ожидание до следующего запланированного поста: {int(sleep_duration)} секунд.")
                time.sleep(sleep_duration)
            else:
                time.sleep(5)
                continue

            current_time_after_sleep = datetime.now(TIMEZONE_MSK)
            if current_time_after_sleep.hour >= END_HOUR or current_time_after_sleep.hour < START_HOUR:
                logging.info("Рабочее время (08:00-23:00 МСК) закончилось. Переход в режим ожидания до утра.")
                continue

            logging.info("Начинаю проверку новостей для публикации...")
            articles = fetch_news_from_api()

            article_to_post = get_best_article_to_post(articles)

            if article_to_post:
                title_ru = article_to_post.get('title')
                description_ru = article_to_post.get('description')
                image_url = article_to_post.get('urlToImage')

                final_description = clean_description(description_ru)

                send_content_to_tg(bot, title_ru, final_description, image_url)

                headline_key = get_headline_key(title_ru)
                save_posted_headline(headline_key)

            else:
                logging.info(
                    "Новостей, подходящих для публикации, не найдено. Пауза до следующего запланированного времени.")

            time.sleep(5)

        except Exception as e:
            logging.critical(f"Критическая ошибка в главном цикле: {e}. Пауза 60 секунд.")
            time.sleep(60)


if __name__ == "__main__":
    main()