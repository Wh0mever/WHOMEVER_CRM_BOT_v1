import os
from telethon import TelegramClient, events
from loguru import logger
import Config
from database.db import Database
from handlers.admin import AdminHandler
from handlers.contacts import ContactHandler
from handlers.messages import MessageHandler

# Создаем необходимые директории
os.makedirs(Config.LOGS_DIR, exist_ok=True)
os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)
if Config.SAVE_MEDIA_FILES:
    os.makedirs(Config.MEDIA_DIR, exist_ok=True)

# Настройка логирования
logger.add(
    os.path.join(Config.LOGS_DIR, Config.LOG_FILE), 
    rotation=Config.LOG_MAX_SIZE, 
    level=Config.LOG_LEVEL,
    retention=Config.LOG_BACKUP_COUNT
)

if Config.LOG_TO_CONSOLE:
    logger.add(lambda msg: print(msg, end=""), level=Config.LOG_LEVEL)

def setup_handlers(client: TelegramClient, db: Database):
    """Настройка всех обработчиков"""
    AdminHandler(client, db)
    ContactHandler(client, db)
    MessageHandler(client, db)

async def interactive_auth(client):
    """Интерактивная авторизация с поддержкой 2FA"""
    
    def phone_code_callback():
        """Запрос кода авторизации"""
        code = input("📱 Введите код авторизации из Telegram: ").strip()
        return code
    
    def password_callback():
        """Запрос пароля для 2FA"""
        import getpass
        password = getpass.getpass("🔐 Введите пароль двухфакторной аутентификации: ")
        return password
    
    # Определяем номер телефона
    phone = Config.PHONE_NUMBER
    
    # Если номер не задан в конфиге, спрашиваем у пользователя
    if not phone:
        print("\n📱 Настройка авторизации Telegram")
        print("=" * 40)
        
        while True:
            phone = input("Введите номер телефона (например: +79001234567): ").strip()
            if not phone:
                print("❌ Номер телефона не может быть пустым!")
                continue
            
            # Проверяем формат
            import re
            if not re.match(Config.PHONE_REGEX, phone):
                print("❌ Неверный формат номера телефона!")
                print(f"Используйте формат: {Config.PHONE_FORMATS.get('DEFAULT', '+XXXXXXXXXXXX')}")
                continue
            
            # Обновляем конфиг
            Config.PHONE_NUMBER = phone
            break
    
    try:
        print(f"\n🔐 Авторизация для номера: {phone}")
        
        # Подключаемся с интерактивными callback'ами
        await client.start(
            phone=phone,
            code_callback=phone_code_callback,
            password=password_callback
        )
        
        logger.info("✅ Авторизация успешно завершена!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка авторизации: {e}")
        return False

async def main():
    # Проверяем базовые настройки (API_ID и API_HASH обязательны)
    if not Config.API_ID or Config.API_ID == 0:
        print("❌ API_ID не установлен в Config.py!")
        return
    
    if not Config.API_HASH:
        print("❌ API_HASH не установлен в Config.py!")
        return

    # Инициализация базы данных
    db = Database(Config.DATABASE_PATH)
    
    # Получаем параметры подключения
    connection_params = Config.get_connection_params()
    server_config = Config.get_telegram_server_config()
    
    # Инициализация клиента с улучшенными настройками
    client = TelegramClient(
        session=connection_params["session"],
        api_id=connection_params["api_id"],
        api_hash=connection_params["api_hash"],
        device_model=connection_params["device_model"],
        system_version=connection_params["system_version"],
        app_version=connection_params["app_version"],
        lang_code=connection_params["lang_code"],
        system_lang_code=connection_params["system_lang_code"],
        use_ipv6=connection_params["use_ipv6"],
        connection_retries=connection_params["connection_retries"],
        timeout=connection_params["timeout"],
        flood_sleep_threshold=connection_params["flood_sleep_threshold"]
    )
    
    try:
        # Интерактивная авторизация
        if not await interactive_auth(client):
            print("❌ Не удалось авторизоваться!")
            return
        
        logger.info("🚀 Бот успешно подключен к Telegram!")
        
        # Получаем информацию о владельце и обновляем конфигурацию
        me = await client.get_me()
        if not Config.OWNER_ID:
            Config.OWNER_ID = me.id
            logger.info(f"👑 Владелец установлен: {me.first_name} (ID: {me.id})")
        
        if not Config.OWNER_USERNAME and me.username:
            Config.OWNER_USERNAME = me.username
            logger.info(f"📛 Username владельца: @{me.username}")
        
        # Автоматически добавляем владельца в админы
        if Config.AUTO_ADD_OWNER_AS_ADMIN and not db.is_admin(me.id):
            try:
                username = me.username or me.phone or str(me.id)
                db.add_admin(username, me.id)
                logger.info(f"🛡️ Владелец добавлен как администратор: @{username}")
            except Exception as e:
                logger.warning(f"Не удалось добавить владельца в админы: {e}")
        
        # Настраиваем обработчики
        setup_handlers(client, db)
        logger.info("⚙️ Обработчики успешно настроены!")
        
        # Выводим информацию о конфигурации
        Config.print_config_info()
        
        print("\n✅ Бот готов к работе!")
        print("📱 Отправьте /start боту в Telegram для начала работы")
        
        # Запускаем прослушивание событий
        await client.run_until_disconnected()
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        logger.exception("Детали ошибки:")
    finally:
        try:
            await client.disconnect()
        except:
            pass

if __name__ == '__main__':
    # Проверяем, настроен ли бот
    validation_errors = Config.validate_config()
    if validation_errors:
        print("❌ Бот не настроен!")
        print("Ошибки конфигурации:")
        for error in validation_errors:
            print(f"  {error}")
        print("\nОткройте файл Config.py и заполните необходимые настройки.")
        exit(1)
    
    # Запуск бота
    import asyncio
    try:
        print("🚀 Запуск Telegram CRM бота...")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен пользователем.")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        logger.exception("Критическая ошибка при запуске") 