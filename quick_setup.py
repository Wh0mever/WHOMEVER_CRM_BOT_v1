#!/usr/bin/env python3
"""
Быстрая настройка Telegram CRM бота
Этот скрипт поможет настроить Config.py
"""

import os
import re

def update_config_file():
    """Обновление файла Config.py с пользовательскими данными"""
    
    print("🤖 Быстрая настройка Telegram CRM бота")
    print("="*50)
    
    # Получаем данные от пользователя
    print("\n📱 Настройка API данных Telegram:")
    print("Получите эти данные на https://my.telegram.org")
    
    api_id = input("Введите API_ID: ").strip()
    api_hash = input("Введите API_HASH: ").strip()
    phone = input("Введите номер телефона (например: +79001234567): ").strip()
    
    # Валидация
    try:
        api_id = int(api_id)
    except ValueError:
        print("❌ API_ID должен быть числом!")
        return False
    
    if not api_hash:
        print("❌ API_HASH не может быть пустым!")
        return False
    
    if not re.match(r'^\+[1-9]\d{1,14}$', phone):
        print("❌ Неверный формат номера телефона!")
        return False
    
    # Читаем текущий Config.py
    config_path = "Config.py"
    if not os.path.exists(config_path):
        print(f"❌ Файл {config_path} не найден!")
        return False
    
    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Обновляем значения
    content = re.sub(r'API_ID = 0', f'API_ID = {api_id}', content)
    content = re.sub(r'API_HASH = ""', f'API_HASH = "{api_hash}"', content)
    content = re.sub(r'PHONE_NUMBER = ""', f'PHONE_NUMBER = "{phone}"', content)
    
    # Опционально добавляем администраторов
    print("\n👥 Настройка администраторов:")
    add_admins = input("Хотите добавить администраторов сейчас? (y/N): ").lower()
    
    if add_admins in ['y', 'yes', 'да']:
        admin_ids = []
        admin_users = {}
        
        while True:
            admin_id = input("Введите Telegram ID администратора (или Enter для завершения): ").strip()
            if not admin_id:
                break
            
            try:
                admin_id = int(admin_id)
                username = input(f"Введите username для ID {admin_id} (опционально): ").strip()
                
                admin_ids.append(admin_id)
                if username:
                    admin_users[admin_id] = username.replace('@', '')
                    
            except ValueError:
                print("❌ ID должен быть числом!")
                continue
        
        if admin_ids:
            # Обновляем список админов в конфиге
            admin_ids_str = ',\n    '.join([str(id) for id in admin_ids])
            content = re.sub(
                r'ADMIN_IDS = \[\s*#[^\]]*\]',
                f'ADMIN_IDS = [\n    {admin_ids_str}\n]',
                content,
                flags=re.DOTALL
            )
            
            if admin_users:
                admin_users_str = ',\n    '.join([f'{id}: "{username}"' for id, username in admin_users.items()])
                content = re.sub(
                    r'ADMIN_USERS = \{\s*#[^}]*\}',
                    f'ADMIN_USERS = {{\n    {admin_users_str}\n}}',
                    content,
                    flags=re.DOTALL
                )
    
    # Сохраняем обновленный файл
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("\n✅ Конфигурация успешно обновлена!")
        print(f"📁 Файл {config_path} сохранен.")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при сохранении файла: {e}")
        return False

def test_config():
    """Тестирование конфигурации"""
    print("\n🔍 Проверка конфигурации...")
    
    try:
        import Config
        
        errors = Config.validate_config()
        if errors:
            print("❌ Найдены ошибки в конфигурации:")
            for error in errors:
                print(f"  {error}")
            return False
        else:
            print("✅ Конфигурация корректна!")
            Config.print_config_info()
            return True
            
    except ImportError as e:
        print(f"❌ Ошибка импорта Config.py: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка при проверке конфигурации: {e}")
        return False

def main():
    """Основная функция"""
    print("🚀 Добро пожаловать в мастер настройки Telegram CRM!")
    print("Этот скрипт поможет быстро настроить Config.py\n")
    
    # Обновляем конфигурацию
    if not update_config_file():
        print("❌ Настройка не завершена.")
        return
    
    # Тестируем конфигурацию
    if not test_config():
        print("❌ Конфигурация содержит ошибки.")
        return
    
    print("\n🎉 Настройка завершена успешно!")
    print("\nТеперь вы можете запустить бота:")
    print("python main.py")
    print("\nДля управления отправьте /start боту в Telegram")
    
    # Предлагаем запустить бота
    run_now = input("\nЗапустить бота сейчас? (y/N): ").lower()
    if run_now in ['y', 'yes', 'да']:
        print("\n🚀 Запуск бота...")
        os.system("python main.py")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Настройка прервана пользователем.")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}") 