#!/usr/bin/env python3
"""
Универсальный запускатель Telegram CRM системы
Автоматически определяет режим работы (bot/userbot) и запускает соответствующий файл
"""

import os
import sys
import asyncio
import subprocess
from loguru import logger
import Config

def check_requirements():
    """Проверка требований системы"""
    
    # Проверяем Python версию
    if sys.version_info < (3, 8):
        print("❌ Требуется Python 3.8 или выше!")
        return False
    
    # Проверяем наличие необходимых модулей
    required_modules = ['telethon', 'aiogram', 'loguru', 'sqlite3']
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    if missing_modules:
        print(f"❌ Отсутствуют модули: {', '.join(missing_modules)}")
        print("Установите их командой: pip install -r requirements.txt")
        return False
    
    return True

def create_directories():
    """Создание необходимых директорий"""
    directories = [
        Config.LOGS_DIR,
        os.path.dirname(Config.DATABASE_PATH),
        Config.MEDIA_DIR if Config.SAVE_MEDIA_FILES else None
    ]
    
    for directory in directories:
        if directory:
            os.makedirs(directory, exist_ok=True)

def show_config_info():
    """Показать информацию о текущей конфигурации"""
    print("\n" + "="*60)
    print("🚀 TELEGRAM CRM СИСТЕМА")
    print("="*60)
    
    Config.print_config_info()
    
    # Проверяем конфигурацию
    validation_errors = Config.validate_config()
    if validation_errors:
        print("\n❌ ОШИБКИ КОНФИГУРАЦИИ:")
        for error in validation_errors:
            print(f"  {error}")
        print("\n🔧 Откройте файл Config.py и исправьте ошибки.")
        return False
    
    print("✅ Конфигурация корректна!")
    return True

def start_bot_mode():
    """Запуск в режиме обычного бота"""
    print("\n🤖 Запуск в режиме обычного бота...")
    try:
        subprocess.run([sys.executable, "main_bot.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка запуска бота: {e}")
        return False
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен пользователем.")
    return True

def start_userbot_mode():
    """Запуск в режиме userbot"""
    print("\n👤 Запуск в режиме userbot...")
    try:
        subprocess.run([sys.executable, "main.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка запуска userbot: {e}")
        return False
    except KeyboardInterrupt:
        print("\n👋 Userbot остановлен пользователем.")
    return True

def select_mode():
    """Интерактивный выбор режима работы"""
    
    while True:
        print("\n" + "="*40)
        print("🔧 ВЫБОР РЕЖИМА РАБОТЫ")
        print("="*40)
        print("1. 🤖 Обычный бот (рекомендуется)")
        print("   • Работает с токеном от @BotFather")
        print("   • Простая настройка")
        print("   • Стабильная работа")
        print()
        print("2. 👤 Userbot")
        print("   • Работает от личного аккаунта")
        print("   • Требует API_ID и API_HASH")
        print("   • Больше возможностей")
        print()
        print("3. ⚙️ Настроить конфигурацию")
        print("4. ❌ Выход")
        print()
        
        choice = input("Выберите опцию (1-4): ").strip()
        
        if choice == "1":
            Config.BOT_MODE = "bot"
            return "bot"
        elif choice == "2":
            Config.BOT_MODE = "userbot"
            return "userbot"
        elif choice == "3":
            subprocess.run([sys.executable, "quick_setup.py"])
            continue
        elif choice == "4":
            return None
        else:
            print("❌ Неверный выбор! Попробуйте снова.")

def main():
    """Главная функция"""
    
    print("🚀 Telegram CRM System Launcher")
    print("=" * 50)
    
    # Проверяем требования
    if not check_requirements():
        input("\nНажмите Enter для выхода...")
        return
    
    # Создаем директории
    create_directories()
    
    # Показываем информацию о конфигурации
    if not show_config_info():
        input("\nНажмите Enter для выхода...")
        return
    
    # Определяем режим работы
    mode = Config.BOT_MODE
    
    # Если режим не установлен или некорректный, спрашиваем у пользователя
    if mode not in ["bot", "userbot"]:
        mode = select_mode()
        if not mode:
            print("👋 Выход из программы.")
            return
    
    print(f"\n🎯 Выбран режим: {mode.upper()}")
    
    # Дополнительная проверка конфигурации для выбранного режима
    if mode == "bot":
        if not Config.BOT_TOKEN:
            print("❌ Не установлен BOT_TOKEN для режима обычного бота!")
            print("Получите токен у @BotFather и добавьте в Config.py")
            input("\nНажмите Enter для выхода...")
            return
        
        print("✅ Готов к запуску обычного бота")
        input("\nНажмите Enter для запуска...")
        start_bot_mode()
        
    elif mode == "userbot":
        if not Config.API_ID or not Config.API_HASH:
            print("❌ Не установлены API_ID или API_HASH для режима userbot!")
            print("Получите их на https://my.telegram.org и добавьте в Config.py")
            input("\nНажмите Enter для выхода...")
            return
        
        print("✅ Готов к запуску userbot")
        input("\nНажмите Enter для запуска...")
        start_userbot_mode()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Программа завершена пользователем.")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        logger.exception("Критическая ошибка в launcher")
        input("\nНажмите Enter для выхода...") 