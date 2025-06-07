import os
from typing import Optional

class Settings:
    # Telegram API настройки
    API_ID: Optional[int] = None  # Ваш API ID от Telegram
    API_HASH: Optional[str] = None  # Ваш API Hash от Telegram
    PHONE: Optional[str] = None  # Ваш номер телефона

    # Настройки базы данных
    DATABASE_PATH: str = "telegram_crm.db"
    
    # Настройки логирования
    LOGS_DIR: str = "logs"
    LOG_FILE: str = os.path.join(LOGS_DIR, "debug.log")
    LOG_LEVEL: str = "DEBUG"
    LOG_ROTATION: str = "1 MB"

    # Настройки приложения
    SESSION_NAME: str = "telegram_crm_session"
    
    # Лимиты и ограничения
    MESSAGE_HISTORY_LIMIT: int = 20  # Количество сообщений в истории
    CONTACTS_PER_PAGE: int = 10  # Количество контактов на странице
    MESSAGE_SEND_DELAY: int = 3  # Задержка между отправкой сообщений (в секундах)

    # Форматы
    PHONE_FORMAT: str = "+7XXXXXXXXXX"  # Формат номера телефона
    DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"  # Формат даты и времени

    @classmethod
    def setup(cls, api_id: int, api_hash: str, phone: str):
        """Установка основных параметров конфигурации"""
        cls.API_ID = api_id
        cls.API_HASH = api_hash
        cls.PHONE = phone

        # Создаем директорию для логов, если её нет
        if not os.path.exists(cls.LOGS_DIR):
            os.makedirs(cls.LOGS_DIR)

    @classmethod
    def validate(cls) -> bool:
        """Проверка наличия всех необходимых настроек"""
        return all([
            cls.API_ID is not None,
            cls.API_HASH is not None,
            cls.PHONE is not None
        ])

# Создаем экземпляр настроек
settings = Settings() 