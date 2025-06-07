#!/usr/bin/env python3
"""
Скрипт для первоначальной настройки Telegram CRM бота
"""

import os
import asyncio
from telethon import TelegramClient
from config import settings
from database import Database

async def setup_initial_config():
    """Настройка начальной конфигурации"""
    print("🚀 Настройка Telegram CRM бота")
    print("=" * 40)
    
    # Получаем данные от пользователя
    api_id = input("Введите API_ID: ").strip()
    api_hash = input("Введите API_HASH: ").strip()
    phone = input("Введите номер телефона: ").strip()
    
    try:
        api_id = int(api_id)
    except ValueError:
        print("❌ API_ID должен быть числом!")
        return False
    
    # Настраиваем конфигурацию
    settings.setup(api_id, api_hash, phone)
    
    if not settings.validate():
        print("❌ Некорректные данные конфигурации!")
        return False
    
    print("\n✅ Конфигурация установлена успешно!")
    return True

async def setup_first_admin():
    """Добавление первого администратора"""
    print("\n👤 Добавление первого администратора")
    print("=" * 40)
    
    # Инициализация базы данных
    db = Database(settings.DATABASE_PATH)
    
    # Проверяем, есть ли уже администраторы
    admins = db.get_all_admins()
    if admins:
        print(f"⚠️ В системе уже есть {len(admins)} администратор(ов):")
        for admin in admins:
            print(f"   - @{admin.username}")
        
        add_another = input("\nДобавить еще одного администратора? (y/N): ").lower()
        if add_another not in ['y', 'yes', 'да']:
            return True
    
    # Инициализация клиента для получения информации о пользователе
    client = TelegramClient(settings.SESSION_NAME, settings.API_ID, settings.API_HASH)
    
    try:
        await client.start(phone=settings.PHONE)
        print("✅ Подключение к Telegram установлено!")
        
        # Получаем информацию о владельце аккаунта
        me = await client.get_me()
        print(f"\n👋 Привет, {me.first_name}!")
        
        # Предлагаем добавить владельца как первого админа
        add_owner = input(f"Добавить вас (@{me.username or me.phone}) как администратора? (Y/n): ").lower()
        
        if add_owner not in ['n', 'no', 'нет']:
            username = me.username or me.phone or str(me.id)
            db.add_admin(username, me.id)
            print(f"✅ Вы добавлены как администратор: @{username}")
        
        # Предлагаем добавить других админов
        while True:
            add_more = input("\nДобавить другого администратора? (y/N): ").lower()
            if add_more not in ['y', 'yes', 'да']:
                break
            
            username = input("Введите username администратора (без @): ").strip()
            try:
                user = await client.get_entity(username)
                
                if db.is_admin(user.id):
                    print(f"⚠️ @{username} уже является администратором!")
                    continue
                
                db.add_admin(username, user.id)
                print(f"✅ @{username} добавлен как администратор!")
                
            except Exception as e:
                print(f"❌ Ошибка при добавлении @{username}: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при подключении к Telegram: {e}")
        return False
    finally:
        await client.disconnect()

async def main():
    """Основная функция настройки"""
    print("🤖 Добро пожаловать в мастер настройки Telegram CRM!")
    print("Этот скрипт поможет настроить бота для работы.\n")
    
    # Шаг 1: Настройка конфигурации
    if not await setup_initial_config():
        print("❌ Настройка не завершена.")
        return
    
    # Шаг 2: Добавление администраторов
    if not await setup_first_admin():
        print("❌ Ошибка при добавлении администраторов.")
        return
    
    print("\n🎉 Настройка завершена успешно!")
    print("\nТеперь вы можете запустить бота командой:")
    print("python main.py")
    print("\nДля управления используйте команду /start в Telegram")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Настройка прервана пользователем.")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}") 