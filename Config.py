#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Конфигурационный файл для Telegram CRM бота
Здесь находятся все основные настройки системы
"""

# =================================================================
# 🔑 ОСНОВНЫЕ API НАСТРОЙКИ TELEGRAM
# =================================================================

# Режим работы: "userbot" или "bot"
BOT_MODE = "bot"  # "userbot" - работает от личного аккаунта, "bot" - обычный бот

# === ДЛЯ РЕЖИМА BOT ===
# Токен бота от @BotFather
BOT_TOKEN = "OOO WHOMEVER"

# === ДЛЯ РЕЖИМА USERBOT ===
# Получите эти данные на https://my.telegram.org
API_ID = OOO WHOMEVER  # Ваш API ID (число)
API_HASH = "OOO WHOMEVER"  # Ваш API Hash (строка)

# Номер телефона владельца аккаунта (только для userbot)
PHONE_NUMBER = "+998901242797"  # Формат: "+79001234567"

# Название сессии (можно не менять)
SESSION_NAME = "telegram_crm_session"

# =================================================================
# 🌐 НАСТРОЙКИ MTPROTO СЕРВЕРОВ
# =================================================================

# Конфигурация серверов Telegram
TELEGRAM_SERVERS = {
    "test": {
        "ip": "1111",
        "port": 111,
        "dc_id": 2,
        "public_key": """-----BEGIN RSA PUBLIC KEY-----
123123BEGIN RSA PUBLIC KEY
-----END RSA PUBLIC KEY-----"""
    },
    "production": {
        "ip": "111", 
        "port": 11,
        "dc_id": 1,
        "public_key": """-----BEGIN RSA PUBLIC KEY-----
123123BEGIN RSA PUBLIC KEY
-----END RSA PUBLIC KEY-----"""
    }
}

# Используемый сервер (test или production)
TELEGRAM_SERVER_MODE = "production"

# Дополнительные настройки подключения
CONNECTION_RETRIES = 5
CONNECTION_TIMEOUT = 30
FLOOD_SLEEP_THRESHOLD = 60

# Настройки для улучшения стабильности
USE_IPV6 = False
DEVICE_MODEL = "Desktop"
SYSTEM_VERSION = "Windows 10"
APP_VERSION = "1.0.0"
LANG_CODE = "ru"
SYSTEM_LANG_CODE = "ru-RU"

# =================================================================
# 👑 ВЛАДЕЛЕЦ БОТА
# =================================================================

# ID владельца бота (получается автоматически после первого запуска)
OWNER_ID = 0  # Telegram User ID владельца

# Username владельца (опционально)
OWNER_USERNAME = ""  # Без @, например: "myusername"

# =================================================================
# 🛡️ АДМИНИСТРАТОРЫ
# =================================================================

# Список администраторов (Telegram User ID)
ADMIN_IDS = [
    # 123456789,  # ID первого админа
    # 987654321,  # ID второго админа
]

# Словарь администраторов с их username (для удобства)
ADMIN_USERS = {
    # 123456789: "admin1_username",
    # 987654321: "admin2_username",
}

# Автоматически добавлять владельца в админы?
AUTO_ADD_OWNER_AS_ADMIN = True

# =================================================================
# 💾 НАСТРОЙКИ БАЗЫ ДАННЫХ
# =================================================================

# Путь к файлу базы данных
DATABASE_PATH = "database/telegram_crm.db"

# Создавать резервные копии БД?
AUTO_BACKUP = True

# Интервал создания бэкапов (в часах)
BACKUP_INTERVAL_HOURS = 24

# Максимальное количество бэкапов для хранения
MAX_BACKUPS = 7

# =================================================================
# 📝 НАСТРОЙКИ ЛОГИРОВАНИЯ
# =================================================================

# Директория для логов
LOGS_DIR = "logs"

# Название основного лог-файла
LOG_FILE = "crm_bot.log"

# Уровень логирования: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL = "INFO"

# Максимальный размер лог-файла перед ротацией
LOG_MAX_SIZE = "10 MB"

# Количество старых лог-файлов для хранения
LOG_BACKUP_COUNT = 5

# Логировать в консоль?
LOG_TO_CONSOLE = True

# =================================================================
# 📊 НАСТРОЙКИ ИНТЕРФЕЙСА
# =================================================================

# Количество контактов на одной странице
CONTACTS_PER_PAGE = 10

# Количество сообщений в истории переписки
MESSAGE_HISTORY_LIMIT = 20

# Максимальная длина текста сообщения для отображения
MAX_MESSAGE_PREVIEW_LENGTH = 100

# Показывать дату в формате
DATE_FORMAT = "%d.%m.%Y %H:%M"

# Часовой пояс (например: "Europe/Moscow")
TIMEZONE = "UTC"

# =================================================================
# ⚡ НАСТРОЙКИ ПРОИЗВОДИТЕЛЬНОСТИ
# =================================================================

# Задержка между отправкой сообщений (в секундах)
MESSAGE_SEND_DELAY = 3

# Максимальное количество попыток отправки сообщения
MAX_SEND_ATTEMPTS = 3

# Таймаут для операций с базой данных (в секундах)
DB_TIMEOUT = 30

# Размер пула подключений к БД
DB_POOL_SIZE = 5

# =================================================================
# 🚦 ЛИМИТЫ И ОГРАНИЧЕНИЯ
# =================================================================

# Максимальное количество новых контактов в час
MAX_NEW_CONTACTS_PER_HOUR = 50

# Максимальное количество сообщений в час
MAX_MESSAGES_PER_HOUR = 100

# Максимальная длина имени контакта
MAX_CONTACT_NAME_LENGTH = 100

# Максимальная длина примечания к контакту
MAX_CONTACT_NOTE_LENGTH = 500

# Максимальная длина текста сообщения
MAX_MESSAGE_LENGTH = 4096

# =================================================================
# 🔧 ДОПОЛНИТЕЛЬНЫЕ НАСТРОЙКИ
# =================================================================

# Автоматически добавлять входящие контакты в базу?
AUTO_ADD_INCOMING_CONTACTS = True

# Уведомлять админов о новых входящих сообщениях?
NOTIFY_ADMINS_NEW_MESSAGES = True

# Сохранять медиафайлы?
SAVE_MEDIA_FILES = True

# Директория для сохранения медиафайлов
MEDIA_DIR = "media"

# Автоматически импортировать контакты в Telegram?
AUTO_IMPORT_TO_TELEGRAM = True

# =================================================================
# 🎨 НАСТРОЙКИ ИНТЕРФЕЙСА
# =================================================================

# Эмодзи для различных элементов интерфейса
EMOJI = {
    "contacts": "📇",
    "send_message": "📨", 
    "history": "🗂️",
    "search": "🔍",
    "admins": "📋",
    "statistics": "📊",
    "settings": "⚙️",
    "add": "➕",
    "edit": "✏️",
    "delete": "🗑️",
    "back": "⬅️",
    "success": "✅",
    "error": "❌",
    "warning": "⚠️",
    "info": "ℹ️",
    "user": "👤",
    "phone": "📱",
    "note": "📝",
    "date": "📅",
    "incoming": "📨",
    "outgoing": "📤"
}

# Тексты кнопок
BUTTON_TEXTS = {
    "main_menu": "🏠 Главное меню",
    "contacts_menu": "📇 Контакты", 
    "send_message": "📨 Отправить сообщение",
    "message_history": "🗂️ История переписки",
    "search": "🔍 Поиск",
    "manage_admins": "📋 Управление админами",
    "statistics": "📊 Статистика",
    "settings": "⚙️ Настройки",
    "add_contact": "➕ Добавить контакт",
    "list_contacts": "📋 Список контактов",
    "search_contacts": "🔍 Поиск контактов",
    "back": "⬅️ Назад",
    "cancel": "❌ Отмена",
    "edit": "✏️ Редактировать",
    "delete": "🗑️ Удалить"
}

# =================================================================
# 📱 НАСТРОЙКИ ФОРМАТОВ
# =================================================================

# Регулярное выражение для проверки номера телефона
PHONE_REGEX = r'^\+[1-9]\d{1,14}$'

# Форматы номеров телефонов для разных стран
PHONE_FORMATS = {
    "RU": "+7XXXXXXXXXX",
    "UA": "+380XXXXXXXXX", 
    "BY": "+375XXXXXXXX",
    "KZ": "+77XXXXXXXX",
    "US": "+1XXXXXXXXXX",
    "DEFAULT": "+XXXXXXXXXXXX"
}

# =================================================================
# 🔒 НАСТРОЙКИ БЕЗОПАСНОСТИ
# =================================================================

# Включить дополнительные проверки безопасности?
ENABLE_SECURITY_CHECKS = True

# Логировать все действия администраторов?
LOG_ADMIN_ACTIONS = True

# Максимальное количество неудачных попыток входа
MAX_LOGIN_ATTEMPTS = 3

# Время блокировки после неудачных попыток (в минутах)
LOCKOUT_TIME_MINUTES = 15

# =================================================================
# 📈 НАСТРОЙКИ АНАЛИТИКИ
# =================================================================

# Собирать статистику использования?
COLLECT_USAGE_STATS = True

# Сохранять детальную статистику по сообщениям?
DETAILED_MESSAGE_STATS = True

# Интервал очистки старой статистики (в днях)
STATS_CLEANUP_INTERVAL_DAYS = 90

# =================================================================
# 🚨 НАСТРОЙКИ УВЕДОМЛЕНИЙ
# =================================================================

# Отправлять уведомления о системных событиях?
SYSTEM_NOTIFICATIONS = True

# Уведомлять о новых контактах?
NOTIFY_NEW_CONTACTS = True

# Уведомлять об ошибках?
NOTIFY_ERRORS = True

# =================================================================
# 🔄 АВТОМАТИЧЕСКИЕ ЗАДАЧИ
# =================================================================

# Включить автоматические задачи?
ENABLE_AUTO_TASKS = True

# Автоматически очищать старые логи?
AUTO_CLEANUP_LOGS = True

# Автоматически оптимизировать базу данных?
AUTO_OPTIMIZE_DB = True

# Интервал выполнения автозадач (в часах)
AUTO_TASKS_INTERVAL_HOURS = 6

# =================================================================
# ⚙️ ФУНКЦИИ ВАЛИДАЦИИ
# =================================================================

def validate_config():
    """Проверка корректности конфигурации"""
    errors = []
    
    # Проверяем режим работы
    if BOT_MODE not in ["bot", "userbot"]:
        errors.append("❌ BOT_MODE должен быть 'bot' или 'userbot'")
        return errors
    
    if BOT_MODE == "bot":
        # Проверяем настройки для бота
        if not BOT_TOKEN:
            errors.append("❌ BOT_TOKEN не установлен для режима bot")
    
    elif BOT_MODE == "userbot":
        # Проверяем настройки для userbot
        if not API_ID or API_ID == 0:
            errors.append("❌ API_ID не установлен для режима userbot")
        
        if not API_HASH:
            errors.append("❌ API_HASH не установлен для режима userbot")
        
        if not PHONE_NUMBER:
            errors.append("❌ PHONE_NUMBER не установлен для режима userbot")
        
        # Проверяем формат номера телефона
        import re
        if PHONE_NUMBER and not re.match(PHONE_REGEX, PHONE_NUMBER):
            errors.append("❌ Неверный формат номера телефона")
    
    # Проверяем общие лимиты
    if MESSAGE_SEND_DELAY < 1:
        errors.append("❌ MESSAGE_SEND_DELAY должен быть больше 0")
    
    if CONTACTS_PER_PAGE < 1 or CONTACTS_PER_PAGE > 50:
        errors.append("❌ CONTACTS_PER_PAGE должен быть от 1 до 50")
    
    return errors

def get_all_admin_ids():
    """Получить список всех ID администраторов включая владельца"""
    admin_ids = list(ADMIN_IDS)
    
    if AUTO_ADD_OWNER_AS_ADMIN and OWNER_ID and OWNER_ID not in admin_ids:
        admin_ids.append(OWNER_ID)
    
    return admin_ids

def is_admin(user_id):
    """Проверить, является ли пользователь администратором"""
    return user_id in get_all_admin_ids()

def is_owner(user_id):
    """Проверить, является ли пользователь владельцем"""
    return user_id == OWNER_ID

def get_telegram_server_config():
    """Получить конфигурацию сервера Telegram"""
    return TELEGRAM_SERVERS.get(TELEGRAM_SERVER_MODE, TELEGRAM_SERVERS["production"])

def get_connection_params():
    """Получить параметры подключения для Telethon"""
    server_config = get_telegram_server_config()
    
    return {
        "api_id": API_ID,
        "api_hash": API_HASH,
        "session": SESSION_NAME,
        "device_model": DEVICE_MODEL,
        "system_version": SYSTEM_VERSION,
        "app_version": APP_VERSION,
        "lang_code": LANG_CODE,
        "system_lang_code": SYSTEM_LANG_CODE,
        "use_ipv6": USE_IPV6,
        "connection_retries": CONNECTION_RETRIES,
        "timeout": CONNECTION_TIMEOUT,
        "flood_sleep_threshold": FLOOD_SLEEP_THRESHOLD
    }

# =================================================================
# 📋 ИНФОРМАЦИЯ О КОНФИГУРАЦИИ
# =================================================================

CONFIG_VERSION = "1.0.0"
CONFIG_DESCRIPTION = "Telegram CRM Bot Configuration"

def print_config_info():
    """Вывод информации о текущей конфигурации"""
    server_config = get_telegram_server_config()
    
    print(f"""
🤖 {CONFIG_DESCRIPTION} v{CONFIG_VERSION}
{'='*50}
🔧 Режим: {BOT_MODE.upper()}
📱 Телефон: {PHONE_NUMBER or 'Не установлен'}
🌐 Сервер: {server_config['ip']}:{server_config['port']} (DC {server_config['dc_id']})
👑 Владелец ID: {OWNER_ID or 'Не установлен'}
🛡️ Администраторов: {len(get_all_admin_ids())}
💾 База данных: {DATABASE_PATH}
📝 Логи: {LOGS_DIR}/{LOG_FILE}
⚡ Задержка сообщений: {MESSAGE_SEND_DELAY}с
📊 Контактов на странице: {CONTACTS_PER_PAGE}
🗂️ Сообщений в истории: {MESSAGE_HISTORY_LIMIT}
🔄 Повторы подключения: {CONNECTION_RETRIES}
⏱️ Таймаут: {CONNECTION_TIMEOUT}с
💤 Flood Sleep: {FLOOD_SLEEP_THRESHOLD}с
{'='*50}
    """)

if __name__ == "__main__":
    # При запуске файла показываем информацию о конфигурации
    print_config_info()
    
    # Проверяем конфигурацию
    validation_errors = validate_config()
    if validation_errors:
        print("❌ Ошибки конфигурации:")
        for error in validation_errors:
            print(f"  {error}")
    else:
        print("✅ Конфигурация корректна!") 