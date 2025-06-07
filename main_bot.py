#!/usr/bin/env python3
"""
Главный файл для Telegram CRM бота в режиме обычного бота
"""

import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger
import Config
from database.db import Database
from database.models import Contact, Message as DBMessage
from datetime import datetime
import re

# Добавляем импорт для userbot
from telethon import TelegramClient, types, events
from utils.telegram_contacts import TelegramContactsManager

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

# Инициализация бота и диспетчера
bot = Bot(token=Config.BOT_TOKEN)
dp = Dispatcher()
db = Database(Config.DATABASE_PATH)

# Userbot клиент для автоматического импорта контактов
userbot_client = None
telegram_contacts_manager = None

# Инициализация userbot для импорта контактов
async def init_userbot_for_contacts():
    """Инициализация userbot клиента для автоматического импорта контактов"""
    global userbot_client, telegram_contacts_manager
    
    try:
        if Config.AUTO_IMPORT_TO_TELEGRAM:
            logger.info("🔄 Инициализация userbot для автоматического импорта контактов...")
            
            # Создаем userbot клиент с параметрами подключения
            connection_params = Config.get_connection_params()
            userbot_client = TelegramClient(
                connection_params.pop("session"),  # Убираем session из словаря
                connection_params.pop("api_id"),   # Убираем api_id из словаря  
                connection_params.pop("api_hash"), # Убираем api_hash из словаря
                **connection_params  # Передаем остальные параметры
            )
            
            # Подключаемся
            await userbot_client.start(phone=Config.PHONE_NUMBER)
            
            # Создаем менеджер контактов
            telegram_contacts_manager = TelegramContactsManager(userbot_client)
            
            # Добавляем обработчик входящих сообщений
            @userbot_client.on(events.NewMessage)
            async def handle_userbot_message(event):
                """Обработчик входящих сообщений от userbot"""
                await process_userbot_incoming_message(event)
            
            logger.info("✅ Userbot для импорта контактов инициализирован")
        else:
            logger.info("ℹ️ Автоматический импорт контактов отключен")
            
    except Exception as e:
        logger.error(f"❌ Ошибка при инициализации userbot для контактов: {e}")
        userbot_client = None
        telegram_contacts_manager = None

class BotHandlers:
    """Обработчики для обычного бота"""
    
    @staticmethod
    def get_main_keyboard():
        """Создание главной клавиатуры"""
        builder = InlineKeyboardBuilder()
        
        builder.button(text=Config.BUTTON_TEXTS["contacts_menu"], callback_data="contacts_menu")
        builder.button(text=Config.BUTTON_TEXTS["send_message"], callback_data="message_send")
        builder.button(text=Config.BUTTON_TEXTS["message_history"], callback_data="history_view")
        builder.button(text=Config.BUTTON_TEXTS["search"], callback_data="search_contacts")
        builder.button(text=Config.BUTTON_TEXTS["manage_admins"], callback_data="admin_manage")
        builder.button(text=Config.BUTTON_TEXTS["statistics"], callback_data="stats_view")
        
        builder.adjust(2)  # 2 кнопки в ряд
        return builder.as_markup()
    
    @staticmethod
    def get_contacts_keyboard():
        """Клавиатура для меню контактов"""
        builder = InlineKeyboardBuilder()
        
        builder.button(text=Config.BUTTON_TEXTS["add_contact"], callback_data="contacts_add")
        builder.button(text=Config.BUTTON_TEXTS["list_contacts"], callback_data="contacts_list")
        builder.button(text=Config.BUTTON_TEXTS["search_contacts"], callback_data="contacts_search")
        builder.button(text=Config.BUTTON_TEXTS["back"], callback_data="main_menu")
        
        builder.adjust(2, 1, 1)  # 2 в первом ряду, по 1 в остальных
        return builder.as_markup()
    
    @staticmethod
    def is_admin(user_id: int) -> bool:
        """Проверка прав администратора"""
        return (Config.is_admin(user_id) or 
                db.is_admin(user_id) or
                user_id == Config.OWNER_ID)

async def process_userbot_incoming_message(event):
    """Обработка входящих сообщений через userbot"""
    try:
        # Проверяем что это входящее сообщение от другого пользователя
        if event.is_private and not event.out:
            sender = await event.get_sender()
            sender_id = sender.id
            sender_name = sender.first_name or ""
            if sender.last_name:
                sender_name += f" {sender.last_name}"
            sender_username = sender.username or ""
            
            # Ищем контакт в базе данных
            contact = db.get_contact_by_telegram_id(sender_id)
            
            if contact:
                # Сохраняем входящее сообщение
                db.add_message(
                    contact_id=contact.id,
                    message_id=event.message.id,
                    direction="incoming",
                    text=event.message.text or "[Медиа файл]"
                )
                
                # Уведомляем администраторов
                await notify_admins_about_userbot_message(contact, event.message, sender)
                
                logger.info(f"📨 Входящее сообщение от {contact.name} (ID: {contact.id})")
            else:
                # Если контакт неизвестен, создаем временную запись
                logger.info(f"📨 Сообщение от неизвестного контакта: {sender_name} (ID: {sender_id})")
                
    except Exception as e:
        logger.error(f"Ошибка при обработке входящего сообщения userbot: {e}")

async def notify_admins_about_userbot_message(contact, message, sender):
    """Уведомление администраторов о новом сообщении через userbot"""
    
    # Получаем всех администраторов
    admins = db.get_all_admins()
    
    # Формируем текст сообщения
    message_text = message.text or "[Медиа файл]"
    
    notification_text = (
        f"📨 Новое сообщение!\n\n"
        f"👤 <b>{contact.name}</b>\n"
        f"📱 {contact.phone}\n"
        f"🆔 ID: {contact.id}\n"
        f"📝 Примечание: {contact.note or '-'}\n\n"
        f"💬 <b>Сообщение:</b>\n"
        f"<blockquote>{message_text}</blockquote>\n\n"
        f"⏰ {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    )
    
    # Создаем клавиатуру для быстрого ответа
    builder = InlineKeyboardBuilder()
    builder.button(text="💬 Ответить", callback_data=f"reply_{contact.id}")
    builder.button(text="📖 История", callback_data=f"history_{contact.id}")
    builder.button(text="📇 Карточка", callback_data=f"view_contact_{contact.id}")
    builder.adjust(1)
    
    # Отправляем уведомления всем админам
    for admin in admins:
        try:
            await bot.send_message(
                chat_id=admin.telegram_user_id,
                text=notification_text,
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
            )
            logger.info(f"Уведомление отправлено админу {admin.username}")
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления админу {admin.username}: {e}")

# Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обработка команды /start"""
    
    user_id = message.from_user.id
    
    # Автоматически устанавливаем владельца при первом запуске
    if not Config.OWNER_ID:
        Config.OWNER_ID = user_id
        Config.OWNER_USERNAME = message.from_user.username or str(user_id)
        logger.info(f"👑 Владелец установлен: {message.from_user.full_name} (ID: {user_id})")
        
        # Добавляем владельца в админы (только если еще не добавлен)
        username = message.from_user.username or str(user_id)
        if not db.is_admin(user_id):
            db.add_admin(username, user_id)
            logger.info(f"🛡️ Владелец добавлен как администратор: @{username}")
        
        # Добавляем в Config.ADMIN_IDS
        if user_id not in Config.ADMIN_IDS:
            Config.ADMIN_IDS.append(user_id)
    
    # Проверяем права администратора
    if not BotHandlers.is_admin(user_id):
        await message.reply(
            "⛔ У вас нет прав администратора.\n"
            "Обратитесь к владельцу бота для получения доступа."
        )
        return
    
    # Определяем статус пользователя
    status = "Владелец" if user_id == Config.OWNER_ID else "Администратор"
    
    welcome_text = (
        f"👋 Добро пожаловать в CRM систему!\n\n"
        f"🤖 Режим: Обычный бот\n"
        f"👤 Пользователь: {message.from_user.full_name}\n"
        f"🛡️ Статус: {status}\n\n"
        f"Выберите действие из меню ниже:"
    )
    
    await message.reply(welcome_text, reply_markup=BotHandlers.get_main_keyboard())

# Обработчик команд администрирования
@dp.message(Command("add_admin"))
async def cmd_add_admin(message: Message):
    """Добавление администратора"""
    
    if not BotHandlers.is_admin(message.from_user.id):
        await message.reply("⛔ У вас нет прав для добавления администраторов.")
        return
    
    # Парсим команду
    args = message.text.split()
    if len(args) != 2:
        await message.reply("❌ Использование: /add_admin @username или /add_admin USER_ID")
        return
    
    target = args[1]
    
    try:
        # Пытаемся найти пользователя
        if target.startswith('@'):
            username = target[1:]
            user_id = None  # В обычном боте сложно получить ID по username
        else:
            user_id = int(target)
            username = target
        
        # Добавляем админа
        if user_id:
            db.add_admin(username, user_id)
            Config.ADMIN_IDS.append(user_id)
            await message.reply(f"✅ Пользователь {target} добавлен как администратор!")
        else:
            await message.reply("❌ Для добавления админа нужен Telegram ID (число)")
        
    except ValueError:
        await message.reply("❌ Неверный формат ID пользователя.")
    except Exception as e:
        logger.error(f"Ошибка при добавлении админа: {e}")
        await message.reply("❌ Ошибка при добавлении администратора.")

@dp.message(Command("list_admins"))
async def cmd_list_admins(message: Message):
    """Список администраторов"""
    
    if not BotHandlers.is_admin(message.from_user.id):
        await message.reply("⛔ У вас нет прав для просмотра списка администраторов.")
        return
    
    admins = db.get_all_admins()
    if not admins:
        await message.reply("📋 Список администраторов пуст.")
        return
    
    admin_text = "📋 Список администраторов:\n\n"
    for i, admin in enumerate(admins, 1):
        admin_text += f"{i}. @{admin.username} (ID: {admin.telegram_user_id})\n"
    
    await message.reply(admin_text)

# Обработчик inline кнопок
@dp.callback_query(F.data.startswith(("contacts_", "main_", "message_", "search_", "admin_", "stats_")))
async def process_callback(callback_query: CallbackQuery):
    """Обработка нажатий на inline кнопки"""
    
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    # Проверяем права
    if not BotHandlers.is_admin(user_id):
        await callback_query.answer("⛔ У вас нет прав администратора.", show_alert=True)
        return
    
    try:
        if data == "main_menu":
            # Главное меню
            await callback_query.message.edit_text(
                "🏠 Главное меню CRM системы\n\nВыберите действие:",
                reply_markup=BotHandlers.get_main_keyboard()
            )
        
        elif data == "contacts_menu":
            # Меню контактов
            await callback_query.message.edit_text(
                "📇 Управление контактами\n\nВыберите действие:",
                reply_markup=BotHandlers.get_contacts_keyboard()
            )
        
        elif data == "contacts_add":
            # Добавление контакта
            await callback_query.message.edit_text(
                "➕ Добавление нового контакта\n\n"
                "Отправьте данные контакта в формате:\n"
                "Имя\nТелефон\nПримечание (опционально)\n\n"
                "Пример:\n"
                "Иван Иванов\n"
                "+79001234567\n"
                "ВИП клиент"
            )
        
        elif data == "contacts_list":
            # Список контактов
            contacts = db.get_all_contacts(limit=Config.CONTACTS_PER_PAGE)
            
            if not contacts:
                builder = InlineKeyboardBuilder()
                builder.button(text="⬅️ Назад", callback_data="contacts_menu")
                
                await callback_query.message.edit_text(
                    "📋 Список контактов пуст.",
                    reply_markup=builder.as_markup()
                )
            else:
                contact_text = "📋 Список контактов:\n\n"
                for contact in contacts:
                    contact_text += (
                        f"👤 {contact.name}\n"
                        f"📱 {contact.phone}\n"
                        f"📝 {contact.note or '-'}\n"
                        f"➖➖➖➖➖\n"
                    )
                
                builder = InlineKeyboardBuilder()
                builder.button(text="⬅️ Назад", callback_data="contacts_menu")
                
                await callback_query.message.edit_text(contact_text, reply_markup=builder.as_markup())
        
        elif data == "stats_view":
            # Статистика
            contacts_count = db.get_contacts_count()
            messages_total = db.get_messages_count()
            messages_today = db.get_messages_count_by_period(1)
            messages_week = db.get_messages_count_by_period(7)
            admins_count = len(db.get_all_admins())
            
            stats_text = (
                "📊 Статистика CRM системы\n\n"
                f"👥 Контактов в базе: {contacts_count}\n"
                f"💬 Всего сообщений: {messages_total}\n"
                f"📅 Сообщений сегодня: {messages_today}\n"
                f"📈 Сообщений за неделю: {messages_week}\n"
                f"🛡️ Администраторов: {admins_count}"
            )
            
            builder = InlineKeyboardBuilder()
            builder.button(text="⬅️ Назад", callback_data="main_menu")
            
            await callback_query.message.edit_text(stats_text, reply_markup=builder.as_markup())
        
        elif data == "message_send":
            # Отправка сообщения
            await show_send_message_menu(callback_query)
        
        elif data == "history_view":
            # История переписки
            await show_history_menu(callback_query)
        
        elif data == "search_contacts":
            # Поиск контактов
            await show_search_menu(callback_query)
        
        elif data == "admin_manage":
            # Управление администраторами
            await show_admin_menu(callback_query)
        
        elif data.startswith("remove_admin_"):
            # Подтверждение удаления администратора
            admin_id = int(data.split("_")[2])
            
            admin = next((a for a in db.get_all_admins() if a.telegram_user_id == admin_id), None)
            if admin:
                builder = InlineKeyboardBuilder()
                builder.button(text="✅ Да, удалить", callback_data=f"confirm_remove_{admin_id}")
                builder.button(text="❌ Отмена", callback_data="admin_list")
                builder.adjust(1)
                
                await callback_query.message.edit_text(
                    f"⚠️ Удалить администратора @{admin.username}?\n\n"
                    f"🆔 ID: {admin.telegram_user_id}",
                    reply_markup=builder.as_markup()
                )
            else:
                await callback_query.answer("❌ Администратор не найден", show_alert=True)
        
        elif data.startswith("confirm_remove_"):
            # Подтверждение удаления администратора
            admin_id = int(data.split("_")[2])
            
            try:
                db.remove_admin(admin_id)
                # Удаляем из списка Config
                if admin_id in Config.ADMIN_IDS:
                    Config.ADMIN_IDS.remove(admin_id)
                
                await callback_query.answer("✅ Администратор удален")
                await show_admin_list(callback_query)
                
            except Exception as e:
                logger.error(f"Ошибка при удалении админа: {e}")
                await callback_query.answer("❌ Ошибка при удалении", show_alert=True)
        
        else:
            await callback_query.answer("🚧 Функция в разработке", show_alert=True)
    
    except Exception as e:
        logger.error(f"Ошибка при обработке callback: {e}")
        await callback_query.answer("❌ Произошла ошибка.", show_alert=True)
    
    await callback_query.answer()



async def handle_client_message(message: Message):
    """Обработка сообщения от клиента"""
    user_id = message.from_user.id
    username = message.from_user.username or "Неизвестно"
    full_name = message.from_user.full_name or "Неизвестный пользователь"
    text = message.text
    
    try:
        # Ищем контакт в базе данных
        contact = db.get_contact_by_telegram_id(user_id)
        
        if not contact:
            # Если контакта нет, создаем новый
            phone = f"+{user_id}"  # Временный номер на основе ID
            contact_id = db.add_contact(full_name, phone, f"Telegram: @{username}")
            db.update_contact_telegram_id(contact_id, user_id)
            contact = db.get_contact(contact_id)
            logger.info(f"Создан новый контакт для пользователя {full_name} (ID: {user_id})")
        
        # Сохраняем входящее сообщение
        db.add_message(
            contact_id=contact.id,
            message_id=message.message_id,
            direction="incoming",
            text=text
        )
        
        # Отправляем уведомления всем администраторам
        await notify_admins_about_message(contact, message)
        
        # Отвечаем клиенту
        await message.reply(
            "✅ Ваше сообщение получено и передано менеджеру.\n"
            "Мы свяжемся с вами в ближайшее время!"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения от клиента: {e}")
        await message.reply("❌ Произошла ошибка. Попробуйте позже.")

async def notify_admins_about_message(contact, client_message: Message):
    """Уведомление администраторов о новом сообщении"""
    
    # Получаем всех администраторов
    admins = db.get_all_admins()
    
    notification_text = (
        f"📨 Новое сообщение от клиента!\n\n"
        f"👤 {contact.name}\n"
        f"📱 {contact.phone}\n"
        f"🆔 ID: {contact.id}\n"
        f"📝 Примечание: {contact.note or '-'}\n\n"
        f"💬 Сообщение:\n"
        f"<blockquote>{client_message.text}</blockquote>\n\n"
        f"⏰ {client_message.date.strftime('%d.%m.%Y %H:%M')}"
    )
    
    # Создаем клавиатуру для быстрого ответа
    builder = InlineKeyboardBuilder()
    builder.button(text="📖 История чата", callback_data=f"history_{contact.id}")
    builder.button(text="💬 Быстрый ответ", callback_data=f"reply_{contact.id}")
    builder.button(text="📇 Карточка", callback_data=f"contact_{contact.id}")
    builder.adjust(1)
    
    # Отправляем уведомления всем админам
    for admin in admins:
        try:
            await bot.send_message(
                chat_id=admin.telegram_user_id,
                text=notification_text,
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
            )
            logger.info(f"Уведомление отправлено админу {admin.username}")
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления админу {admin.username}: {e}")

# Добавляем новые callback обработчики
@dp.callback_query(F.data.startswith(("history_", "contact_", "send_reply_", "view_history_")))
async def handle_client_callbacks(callback_query: CallbackQuery):
    """Обработка callback для работы с клиентами"""
    
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    # Проверяем права
    if not BotHandlers.is_admin(user_id):
        await callback_query.answer("⛔ У вас нет прав администратора.", show_alert=True)
        return
    
    try:
        if data == "history_view":
            # История переписки из главного меню
            await show_history_menu(callback_query)
            
        elif data == "history_by_contact":
            # Показать контакты для истории
            await show_contacts_for_history(callback_query)
            
        elif data.startswith("view_history_"):
            # Показать историю конкретного контакта
            contact_id = int(data.split("_")[2])
            await show_chat_history(callback_query, contact_id)
            
        elif data.startswith("history_contacts_page_"):
            # Пагинация контактов для истории
            page = int(data.split("_")[3])
            await show_contacts_for_history(callback_query, page)
            
        elif data == "history_search_contact":
            await callback_query.answer("🔍 Функция поиска для истории в разработке", show_alert=True)
            
        elif data == "history_stats":
            await callback_query.answer("📊 Статистика переписки в разработке", show_alert=True)
            
        elif data.startswith("history_"):
            # Показать историю чата (для контактов с числовым ID)
            try:
                contact_id = int(data.split("_")[1])
                await show_chat_history(callback_query, contact_id)
            except ValueError:
                await callback_query.answer("❌ Неверный формат callback", show_alert=True)
            
        elif data.startswith("contact_"):
            # Показать карточку контакта
            contact_id = int(data.split("_")[1])
            await show_contact_card(callback_query, contact_id)
            
        elif data.startswith("send_reply_"):
            # Отправить ответ (пока заглушка)
            await callback_query.answer("💬 Введите ваш ответ в следующем сообщении", show_alert=True)
            
    except Exception as e:
        logger.error(f"Ошибка при обработке callback для клиента: {e}")
        await callback_query.answer("❌ Произошла ошибка.", show_alert=True)
    
    await callback_query.answer()

async def show_chat_history(callback_query: CallbackQuery, contact_id: int):
    """Показать историю чата с клиентом через userbot"""
    
    contact = db.get_contact(contact_id)
    if not contact:
        await callback_query.answer("❌ Контакт не найден", show_alert=True)
        return

    # Получаем историю через userbot и базу данных
    await callback_query.answer("🔄 Загружаю историю...", show_alert=False)
    
    try:
        # Сначала синхронизируем историю с Telegram через userbot
        if userbot_client and contact.telegram_user_id:
            await sync_chat_history_from_telegram(contact_id, contact.telegram_user_id)
        
        # Получаем обновленную историю из базы
        messages = db.get_contact_messages(contact_id, limit=Config.MESSAGE_HISTORY_LIMIT)
        
        if not messages:
            history_text = f"📖 История чата с {contact.name}\n\n📭 Сообщений пока нет"
        else:
            history_text = f"📖 История чата с {contact.name}\n\n"
            
            # Показываем сообщения в хронологическом порядке (сначала старые)
            for msg in reversed(messages):
                direction_icon = "📤" if msg.direction == "outgoing" else "📨"
                timestamp = msg.timestamp.strftime('%d.%m %H:%M')
                
                # Обрезаем длинные сообщения
                text_preview = msg.text or "[Медиа файл]"
                if len(text_preview) > 80:
                    text_preview = text_preview[:80] + "..."
                
                history_text += f"{direction_icon} <b>{timestamp}</b>\n{text_preview}\n\n"
        
        # Создаем клавиатуру
        builder = InlineKeyboardBuilder()
        builder.button(text="💬 Ответить", callback_data=f"reply_{contact_id}")
        builder.button(text="📇 Карточка", callback_data=f"view_contact_{contact_id}")
        builder.button(text="🔄 Обновить", callback_data=f"history_{contact_id}")
        builder.button(text="🏠 Главное меню", callback_data="main_menu")
        builder.adjust(2, 2)
        
        await callback_query.message.edit_text(
            history_text, 
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при загрузке истории чата: {e}")
        await callback_query.message.edit_text(
            f"❌ Ошибка при загрузке истории чата с {contact.name}",
            reply_markup=InlineKeyboardBuilder().button(text="🏠 Главное меню", callback_data="main_menu").as_markup()
        )

async def sync_chat_history_from_telegram(contact_id: int, telegram_user_id: int):
    """Синхронизация истории чата с Telegram через userbot"""
    try:
        if not userbot_client:
            return
            
        # Получаем последние сообщения из чата через userbot
        async for message in userbot_client.iter_messages(telegram_user_id, limit=50):
            # Проверяем, есть ли уже это сообщение в базе
            existing_message = db.get_message_by_id(contact_id, message.id)
            
            if not existing_message:
                # Определяем направление сообщения
                direction = "outgoing" if message.out else "incoming"
                
                # Сохраняем сообщение в базу
                db.add_message(
                    contact_id=contact_id,
                    message_id=message.id,
                    direction=direction,
                    text=message.text or "[Медиа файл]"
                )
                
        logger.info(f"📋 История чата синхронизирована для контакта ID: {contact_id}")
                
    except Exception as e:
        logger.error(f"Ошибка синхронизации истории чата: {e}")

async def show_reply_interface(callback_query: CallbackQuery, contact_id: int):
    """Показать интерфейс для ответа клиенту"""
    
    contact = db.get_contact(contact_id)
    if not contact:
        await callback_query.answer("❌ Контакт не найден", show_alert=True)
        return
    
    reply_text = (
        f"💬 Ответ клиенту: {contact.name}\n\n"
        f"📱 {contact.phone}\n"
        f"📝 {contact.note or 'Без примечаний'}\n\n"
        f"✍️ Напишите ваш ответ в следующем сообщении.\n"
        f"Он будет автоматически отправлен клиенту."
    )
    
    # Сохраняем ID контакта для следующего сообщения
    # В реальном проекте лучше использовать состояния (FSM)
    callback_query.message.reply_to_contact_id = contact_id
    
    builder = InlineKeyboardBuilder()
    builder.button(text="📖 История", callback_data=f"history_{contact_id}")
    builder.button(text="📇 Карточка", callback_data=f"contact_{contact_id}")
    builder.button(text="❌ Отмена", callback_data="main_menu")
    builder.adjust(2, 1)
    
    await callback_query.message.edit_text(
        reply_text, 
        reply_markup=builder.as_markup()
    )

async def show_contact_card(callback_query: CallbackQuery, contact_id: int):
    """Показать карточку контакта"""
    
    contact = db.get_contact(contact_id)
    if not contact:
        await callback_query.answer("❌ Контакт не найден", show_alert=True)
        return
    
    # Получаем статистику сообщений
    messages = db.get_contact_messages(contact_id, limit=100)
    incoming_count = len([m for m in messages if m.direction == "incoming"])
    outgoing_count = len([m for m in messages if m.direction == "outgoing"])
    
    card_text = (
        f"📇 Карточка контакта\n\n"
        f"👤 <b>Имя:</b> {contact.name}\n"
        f"📱 <b>Телефон:</b> {contact.phone}\n"
        f"📝 <b>Примечание:</b> {contact.note or 'Не указано'}\n"
        f"🆔 <b>ID:</b> {contact.id}\n"
        f"📅 <b>Добавлен:</b> {contact.date_added.strftime('%d.%m.%Y %H:%M')}\n\n"
        f"📊 <b>Статистика:</b>\n"
        f"📨 Входящих: {incoming_count}\n"
        f"📤 Исходящих: {outgoing_count}\n"
        f"💬 Всего: {len(messages)}"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="📖 История", callback_data=f"history_{contact_id}")
    if contact.telegram_user_id:
        builder.button(text="💬 Ответить", callback_data=f"reply_{contact_id}")
    else:
        builder.button(text="🔗 Установить Telegram ID", callback_data=f"set_telegram_id_{contact_id}")
    builder.button(text="✏️ Редактировать", callback_data=f"edit_{contact_id}")
    builder.button(text="🏠 Главное меню", callback_data="main_menu")
    builder.adjust(2, 1, 1)
    
    await callback_query.message.edit_text(
        card_text, 
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

# Состояния для различных операций
user_reply_states = {}
user_search_states = {}
user_message_states = {}

# Обновленный обработчик сообщений с проверкой состояния ответа
@dp.message(F.text)
async def handle_text_messages_updated(message: Message):
    """Обновленная обработка текстовых сообщений с поддержкой ответов клиентам"""
    
    user_id = message.from_user.id
    
    # Если это не администратор - обрабатываем как сообщение от клиента
    if not BotHandlers.is_admin(user_id):
        await handle_client_message(message)
        return
    
    # Проверяем, ожидается ли ответ клиенту
    if user_id in user_reply_states:
        contact_id = user_reply_states[user_id]
        await send_reply_to_client(message, contact_id)
        del user_reply_states[user_id]
        return
    
    # Проверяем, ожидается ли поиск
    if user_id in user_search_states:
        await perform_search(message, message.text)
        del user_search_states[user_id]
        return
    
    # Проверяем, ожидается ли отправка сообщения
    if user_id in user_message_states:
        contact_id = user_message_states[user_id]
        await send_message_to_client(message, contact_id)
        del user_message_states[user_id]
        return
    
    # Проверяем, похоже ли на данные контакта
    lines = message.text.strip().split('\n')
    if len(lines) >= 2:
        name = lines[0].strip()
        phone = lines[1].strip()
        note = lines[2].strip() if len(lines) > 2 else None
        
        # Проверяем формат телефона
        if re.match(Config.PHONE_REGEX, phone):
            try:
                # Сначала добавляем контакт в базу
                contact_id = db.add_contact(name, phone, note)
                
                response_text = (
                    f"✅ Контакт успешно добавлен!\n\n"
                    f"👤 Имя: {name}\n"
                    f"📱 Телефон: {phone}\n"
                    f"📝 Примечание: {note if note else '-'}\n"
                    f"🆔 ID в базе: {contact_id}"
                )
                
                # Автоматически добавляем контакт в Telegram и получаем telegram_user_id
                if telegram_contacts_manager:
                    try:
                        telegram_result = await telegram_contacts_manager.add_contact_to_telegram(name, phone)
                        
                        if telegram_result["success"]:
                            # Обновляем telegram_user_id в базе
                            db.update_contact_telegram_id(contact_id, telegram_result["user_id"])
                            
                            username_info = f" (@{telegram_result['username']})" if telegram_result["username"] else ""
                            response_text += f"\n\n📲 <b>Telegram:</b> Найден и добавлен{username_info}"
                            response_text += f"\n✅ <b>Telegram ID:</b> {telegram_result['user_id']}"
                            
                            logger.info(f"📱 Контакт автоматически добавлен в Telegram: {name} -> {telegram_result['user_id']}")
                        else:
                            response_text += f"\n\n⚠️ <b>Telegram:</b> {telegram_result['message']}"
                            response_text += f"\n❌ <b>Telegram ID:</b> Не найден"
                            
                    except Exception as e:
                        logger.warning(f"Не удалось автоматически добавить контакт в Telegram: {e}")
                        response_text += f"\n\n⚠️ <b>Telegram:</b> Ошибка автоматического добавления"
                        response_text += f"\n❌ <b>Telegram ID:</b> Не установлен"
                else:
                    response_text += f"\n\n❌ <b>Telegram ID:</b> Не установлен (userbot не подключен)"
                
                builder = InlineKeyboardBuilder()
                builder.button(text="📇 К контактам", callback_data="contacts_menu")
                builder.button(text="🏠 Главное меню", callback_data="main_menu")
                builder.adjust(1)
                
                await message.reply(response_text, reply_markup=builder.as_markup(), parse_mode="HTML")
                
            except Exception as e:
                logger.error(f"Ошибка при добавлении контакта: {e}")
                await message.reply("❌ Ошибка при добавлении контакта.")
        else:
            await message.reply(
                "❌ Неверный формат номера телефона!\n"
                f"Используйте формат: {Config.PHONE_FORMATS.get('DEFAULT', '+XXXXXXXXXXXX')}"
            )

async def send_reply_to_client(admin_message: Message, contact_id: int):
    """Отправка ответа клиенту"""
    
    try:
        contact = db.get_contact(contact_id)
        if not contact or not contact.telegram_user_id:
            await admin_message.reply("❌ Не удалось найти клиента или у него нет Telegram ID")
            return
        
        # Отправляем сообщение клиенту через userbot
        if userbot_client:
            sent_message = await userbot_client.send_message(
                entity=contact.telegram_user_id,
                message=admin_message.text
            )
            message_id = sent_message.id
        else:
            # Если userbot недоступен, пробуем через обычный бот
            sent_message = await bot.send_message(
                chat_id=contact.telegram_user_id,
                text=admin_message.text
            )
            message_id = sent_message.message_id
        
        # Сохраняем исходящее сообщение в базу
        db.add_message(
            contact_id=contact_id,
            message_id=message_id,
            direction="outgoing",
            text=admin_message.text
        )
        
        # Подтверждение админу
        builder = InlineKeyboardBuilder()
        builder.button(text="📖 История", callback_data=f"history_{contact_id}")
        builder.button(text="📇 Карточка", callback_data=f"contact_{contact_id}")
        builder.button(text="🏠 Главное меню", callback_data="main_menu")
        builder.adjust(2, 1)
        
        await admin_message.reply(
            f"✅ Ответ отправлен клиенту {contact.name}",
            reply_markup=builder.as_markup()
        )
        
        logger.info(f"Ответ отправлен клиенту {contact.name} (ID: {contact_id})")
        
    except Exception as e:
        logger.error(f"Ошибка при отправке ответа клиенту: {e}")
        await admin_message.reply("❌ Ошибка при отправке ответа клиенту")

async def send_message_to_client(admin_message: Message, contact_id: int):
    """Отправка нового сообщения клиенту"""
    
    try:
        contact = db.get_contact(contact_id)
        if not contact or not contact.telegram_user_id:
            await admin_message.reply("❌ Не удалось найти клиента или у него нет Telegram ID")
            return
        
        # Отправляем сообщение клиенту через userbot
        if userbot_client:
            sent_message = await userbot_client.send_message(
                entity=contact.telegram_user_id,
                message=admin_message.text
            )
        else:
            # Если userbot недоступен, пробуем через обычный бот
            sent_message = await bot.send_message(
                chat_id=contact.telegram_user_id,
                text=admin_message.text
            )
        
        # Сохраняем исходящее сообщение в базу
        message_id = sent_message.id if hasattr(sent_message, 'id') else sent_message.message_id
        db.add_message(
            contact_id=contact_id,
            message_id=message_id,
            direction="outgoing",
            text=admin_message.text
        )
        
        # Подтверждение админу
        builder = InlineKeyboardBuilder()
        builder.button(text="📖 История", callback_data=f"history_{contact_id}")
        builder.button(text="📇 Карточка", callback_data=f"contact_{contact_id}")
        builder.button(text="📨 Отправить еще", callback_data=f"send_to_{contact_id}")
        builder.button(text="🏠 Главное меню", callback_data="main_menu")
        builder.adjust(2, 1, 1)
        
        await admin_message.reply(
            f"✅ Сообщение отправлено клиенту {contact.name}",
            reply_markup=builder.as_markup()
        )
        
        logger.info(f"Сообщение отправлено клиенту {contact.name} (ID: {contact_id})")
        
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения клиенту: {e}")
        await admin_message.reply("❌ Ошибка при отправке сообщения клиенту")

# Обновляем обработчик reply callback
@dp.callback_query(F.data.startswith("reply_"))
async def handle_reply_callback(callback_query: CallbackQuery):
    """Обработка нажатия кнопки 'Ответить'"""
    
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    if not BotHandlers.is_admin(user_id):
        await callback_query.answer("⛔ У вас нет прав администратора.", show_alert=True)
        return
    
    try:
        contact_id = int(data.split("_")[1])
        contact = db.get_contact(contact_id)
        
        if not contact:
            await callback_query.answer("❌ Контакт не найден", show_alert=True)
            return
        
        # Устанавливаем состояние ожидания ответа
        user_reply_states[user_id] = contact_id
        
        reply_text = (
            f"💬 Ответ клиенту: <b>{contact.name}</b>\n\n"
            f"📱 {contact.phone}\n"
            f"📝 {contact.note or 'Без примечаний'}\n\n"
            f"✍️ Напишите ваш ответ в следующем сообщении.\n"
            f"Он будет автоматически отправлен клиенту."
        )
        
        builder = InlineKeyboardBuilder()
        builder.button(text="📖 История", callback_data=f"history_{contact_id}")
        builder.button(text="📇 Карточка", callback_data=f"contact_{contact_id}")
        builder.button(text="❌ Отмена", callback_data=f"cancel_reply_{contact_id}")
        builder.adjust(2, 1)
        
        await callback_query.message.edit_text(
            reply_text, 
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
        
        await callback_query.answer("✍️ Ожидаю ваш ответ...")
        
    except Exception as e:
        logger.error(f"Ошибка при обработке reply callback: {e}")
        await callback_query.answer("❌ Произошла ошибка.", show_alert=True)

# Обработчик отмены ответа
@dp.callback_query(F.data.startswith("cancel_reply_"))
async def handle_cancel_reply(callback_query: CallbackQuery):
    """Отмена ответа клиенту"""
    
    user_id = callback_query.from_user.id
    
    # Удаляем состояние ожидания ответа
    if user_id in user_reply_states:
        del user_reply_states[user_id]
    
    await callback_query.answer("❌ Ответ отменен")
    
    # Возвращаемся к главному меню
    await callback_query.message.edit_text(
        "🏠 Главное меню CRM системы\n\nВыберите действие:",
        reply_markup=BotHandlers.get_main_keyboard()
    )

# Дополнительные обработчики callback
@dp.callback_query(F.data.startswith(("send_", "admin_", "history_", "view_", "set_telegram_id_")))
async def handle_additional_callbacks(callback_query: CallbackQuery):
    """Обработка дополнительных callback"""
    
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    if not BotHandlers.is_admin(user_id):
        await callback_query.answer("⛔ У вас нет прав администратора.", show_alert=True)
        return
    
    try:
        # === ОТПРАВКА СООБЩЕНИЙ ===
        if data == "send_by_contact":
            await show_contact_list_for_sending(callback_query)
        
        elif data.startswith("send_contacts_page_"):
            page = int(data.split("_")[-1])
            await show_contact_list_for_sending(callback_query, page)
        
        elif data.startswith("send_to_"):
            contact_id = int(data.split("_")[2])
            contact = db.get_contact(contact_id)
            
            if not contact:
                await callback_query.answer("❌ Контакт не найден", show_alert=True)
                return
            
            # Устанавливаем состояние отправки сообщения
            user_message_states[user_id] = contact_id
            
            await callback_query.message.edit_text(
                f"📨 Отправка сообщения контакту:\n\n"
                f"👤 {contact.name}\n"
                f"📱 {contact.phone}\n\n"
                f"✍️ Напишите ваше сообщение:"
            )
            await callback_query.answer("✍️ Ожидаю ваше сообщение...")
        
        # === ИСТОРИЯ ПЕРЕПИСКИ ===
        elif data == "history_by_contact":
            await show_contacts_for_history(callback_query)
        
        elif data.startswith("history_contacts_page_"):
            page = int(data.split("_")[-1])
            await show_contacts_for_history(callback_query, page)
        
        elif data.startswith("view_history_"):
            contact_id = int(data.split("_")[2])
            await show_chat_history(callback_query, contact_id)
        
        elif data.startswith("view_contact_"):
            contact_id = int(data.split("_")[2])
            await show_contact_card(callback_query, contact_id)
        
        elif data.startswith("set_telegram_id_"):
            # Установка Telegram ID для контакта
            contact_id = int(data.split("_")[3])
            contact = db.get_contact(contact_id)
            
            if not contact:
                await callback_query.answer("❌ Контакт не найден", show_alert=True)
                return
            
            await callback_query.answer("🔍 Ищу контакт в Telegram...", show_alert=False)
            
            # Ищем контакт в Telegram через userbot
            if telegram_contacts_manager:
                try:
                    telegram_result = await telegram_contacts_manager.add_contact_to_telegram(contact.name, contact.phone)
                    
                    if telegram_result["success"]:
                        # Обновляем telegram_user_id в базе
                        db.update_contact_telegram_id(contact_id, telegram_result["user_id"])
                        
                        username_info = f" (@{telegram_result['username']})" if telegram_result["username"] else ""
                        
                        success_text = (
                            f"✅ Telegram ID установлен!\n\n"
                            f"👤 <b>Имя:</b> {contact.name}\n"
                            f"📱 <b>Телефон:</b> {contact.phone}\n"
                            f"📝 <b>Примечание:</b> {contact.note or 'Не указано'}\n"
                            f"🆔 <b>ID:</b> {contact.id}\n\n"
                            f"✅ <b>Telegram ID:</b> {telegram_result['user_id']}{username_info}"
                        )
                        
                        builder = InlineKeyboardBuilder()
                        builder.button(text="💬 Написать", callback_data=f"send_to_{contact_id}")
                        builder.button(text="📖 История", callback_data=f"history_{contact_id}")
                        builder.button(text="🏠 Главное меню", callback_data="main_menu")
                        builder.adjust(2, 1)
                        
                        await callback_query.message.edit_text(
                            success_text, 
                            reply_markup=builder.as_markup(),
                            parse_mode="HTML"
                        )
                        
                        logger.info(f"📱 Telegram ID установлен для контакта: {contact.name} -> {telegram_result['user_id']}")
                    else:
                        error_text = (
                            f"❌ Не удалось найти контакт в Telegram\n\n"
                            f"👤 <b>Имя:</b> {contact.name}\n"
                            f"📱 <b>Телефон:</b> {contact.phone}\n"
                            f"📝 <b>Примечание:</b> {contact.note or 'Не указано'}\n\n"
                            f"⚠️ <b>Причина:</b> {telegram_result['message']}"
                        )
                        
                        builder = InlineKeyboardBuilder()
                        builder.button(text="🔍 Попробовать снова", callback_data=f"set_telegram_id_{contact_id}")
                        builder.button(text="🏠 Главное меню", callback_data="main_menu")
                        builder.adjust(1)
                        
                        await callback_query.message.edit_text(
                            error_text, 
                            reply_markup=builder.as_markup(),
                            parse_mode="HTML"
                        )
                        
                except Exception as e:
                    logger.error(f"Ошибка при поиске контакта в Telegram: {e}")
                    await callback_query.message.edit_text(
                        f"❌ Ошибка при поиске контакта в Telegram:\n{str(e)}",
                        reply_markup=InlineKeyboardBuilder().button(
                            text="🏠 Главное меню", callback_data="main_menu"
                        ).as_markup()
                    )
            else:
                await callback_query.message.edit_text(
                    "❌ Userbot не подключен.\nАвтоматический поиск недоступен.",
                    reply_markup=InlineKeyboardBuilder().button(
                        text="🏠 Главное меню", callback_data="main_menu"
                    ).as_markup()
                )
        
        # === УПРАВЛЕНИЕ АДМИНАМИ ===
        elif data == "admin_list":
            await show_admin_list(callback_query)
        
        elif data == "admin_add":
            await callback_query.message.edit_text(
                "➕ Добавление администратора\n\n"
                "Используйте команду: /add_admin USER_ID\n"
                "Где USER_ID - Telegram ID пользователя"
            )
        
        elif data == "admin_remove":
            # Показываем список админов для удаления
            await show_admin_list(callback_query)
        

        
        else:
            await callback_query.answer("🚧 Функция в разработке", show_alert=True)
    
    except Exception as e:
        logger.error(f"Ошибка при обработке callback: {e}")
        await callback_query.answer("❌ Произошла ошибка.", show_alert=True)
    
    await callback_query.answer()

# =================================================================
# 📨 ФУНКЦИИ ОТПРАВКИ СООБЩЕНИЙ
# =================================================================

async def show_send_message_menu(callback_query: CallbackQuery):
    """Показать меню отправки сообщений"""
    
    menu_text = (
        "📨 Отправка сообщения\n\n"
        "Выберите способ отправки:"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="📇 По контакту", callback_data="send_by_contact")
    builder.button(text="📱 По номеру телефона", callback_data="send_by_phone")
    builder.button(text="🔍 Найти контакт", callback_data="send_search_contact")
    builder.button(text="⬅️ Назад", callback_data="main_menu")
    builder.adjust(1)
    
    await callback_query.message.edit_text(menu_text, reply_markup=builder.as_markup())

async def show_contact_list_for_sending(callback_query: CallbackQuery, page: int = 0):
    """Показать список контактов для отправки сообщения"""
    
    offset = page * Config.CONTACTS_PER_PAGE
    contacts = db.get_all_contacts(limit=Config.CONTACTS_PER_PAGE, offset=offset)
    
    if not contacts:
        builder = InlineKeyboardBuilder()
        builder.button(text="⬅️ Назад", callback_data="message_send")
        
        await callback_query.message.edit_text(
            "📋 Контактов не найдено.",
            reply_markup=builder.as_markup()
        )
        return
    
    contact_text = f"📇 Выберите контакт (стр. {page + 1}):\n\n"
    
    builder = InlineKeyboardBuilder()
    for contact in contacts:
        contact_text += f"👤 {contact.name} - {contact.phone}\n"
        builder.button(
            text=f"{contact.name}",
            callback_data=f"send_to_{contact.id}"
        )
    
    # Навигация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"send_contacts_page_{page-1}"))
    
    # Проверяем есть ли еще контакты
    next_contacts = db.get_all_contacts(limit=1, offset=(page + 1) * Config.CONTACTS_PER_PAGE)
    if next_contacts:
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"send_contacts_page_{page+1}"))
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    builder.button(text="⬅️ Назад", callback_data="message_send")
    builder.adjust(1)
    
    await callback_query.message.edit_text(contact_text, reply_markup=builder.as_markup())

# =================================================================
# 🗂️ ФУНКЦИИ ИСТОРИИ ПЕРЕПИСКИ  
# =================================================================

async def show_history_menu(callback_query: CallbackQuery):
    """Показать меню истории переписки"""
    
    menu_text = (
        "🗂️ История переписки\n\n"
        "Выберите контакт для просмотра истории:"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="📇 По контакту", callback_data="history_by_contact")
    builder.button(text="🔍 Найти контакт", callback_data="history_search_contact")
    builder.button(text="📊 Статистика переписки", callback_data="history_stats")
    builder.button(text="⬅️ Назад", callback_data="main_menu")
    builder.adjust(1)
    
    await callback_query.message.edit_text(menu_text, reply_markup=builder.as_markup())

async def show_contacts_for_history(callback_query: CallbackQuery, page: int = 0):
    """Показать список контактов для просмотра истории"""
    
    offset = page * Config.CONTACTS_PER_PAGE
    contacts = db.get_all_contacts(limit=Config.CONTACTS_PER_PAGE, offset=offset)
    
    if not contacts:
        builder = InlineKeyboardBuilder()
        builder.button(text="⬅️ Назад", callback_data="history_view")
        
        await callback_query.message.edit_text(
            "📋 Контактов не найдено.",
            reply_markup=builder.as_markup()
        )
        return
    
    contact_text = f"📇 Выберите контакт (стр. {page + 1}):\n\n"
    
    builder = InlineKeyboardBuilder()
    for contact in contacts:
        # Получаем количество сообщений
        messages = db.get_contact_messages(contact.id, limit=1)
        msg_count = len(db.get_contact_messages(contact.id, limit=1000))
        
        contact_text += f"👤 {contact.name} - {contact.phone} ({msg_count} сообщ.)\n"
        builder.button(
            text=f"{contact.name} ({msg_count})",
            callback_data=f"view_history_{contact.id}"
        )
    
    # Навигация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"history_contacts_page_{page-1}"))
    
    next_contacts = db.get_all_contacts(limit=1, offset=(page + 1) * Config.CONTACTS_PER_PAGE)
    if next_contacts:
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"history_contacts_page_{page+1}"))
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    builder.button(text="⬅️ Назад", callback_data="history_view")
    builder.adjust(1)
    
    await callback_query.message.edit_text(contact_text, reply_markup=builder.as_markup())

# =================================================================
# 🔍 ФУНКЦИИ ПОИСКА
# =================================================================

async def show_search_menu(callback_query: CallbackQuery):
    """Показать меню поиска"""
    
    menu_text = (
        "🔍 Поиск контактов\n\n"
        "Введите запрос для поиска:\n"
        "• По имени\n"
        "• По номеру телефона\n"
        "• По примечанию"
    )
    
    # Устанавливаем состояние поиска
    user_search_states[callback_query.from_user.id] = True
    
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="main_menu")
    
    await callback_query.message.edit_text(menu_text, reply_markup=builder.as_markup())

async def perform_search(message: Message, query: str):
    """Выполнить поиск контактов"""
    
    try:
        contacts = db.search_contacts(query)
        
        if not contacts:
            builder = InlineKeyboardBuilder()
            builder.button(text="🔍 Новый поиск", callback_data="search_contacts")
            builder.button(text="🏠 Главное меню", callback_data="main_menu")
            builder.adjust(1)
            
            await message.reply(
                f"🔍 По запросу '{query}' ничего не найдено.",
                reply_markup=builder.as_markup()
            )
            return
        
        if len(contacts) == 1:
            # Если найден только один контакт, сразу показываем его карточку
            contact = contacts[0]
            await show_contact_card_from_search(message, contact)
            return
        
        result_text = f"🔍 Результаты поиска по '{query}' ({len(contacts)} найдено):\n\n"
        
        builder = InlineKeyboardBuilder()
        
        for i, contact in enumerate(contacts[:10], 1):  # Показываем первые 10
            # Проверяем есть ли у контакта Telegram ID
            telegram_status = "✅" if contact.telegram_user_id else "❌"
            
            result_text += (
                f"{i}. 👤 <b>{contact.name}</b>\n"
                f"📱 {contact.phone}\n"
                f"📝 {contact.note or '-'}\n"
                f"📨 Telegram: {telegram_status}\n\n"
            )
            
            # Создаем кнопки для каждого контакта
            builder.button(
                text=f"📇 {contact.name}",
                callback_data=f"view_contact_{contact.id}"
            )
        
        if len(contacts) > 10:
            result_text += f"... и еще {len(contacts) - 10} контактов"
        
        # Кнопки навигации
        builder.button(text="🔍 Новый поиск", callback_data="search_contacts")
        builder.button(text="🏠 Главное меню", callback_data="main_menu")
        builder.adjust(2, 2, 1)  # По 2 кнопки для контактов, потом навигация
        
        await message.reply(result_text, reply_markup=builder.as_markup(), parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Ошибка при поиске: {e}")
        await message.reply("❌ Ошибка при поиске контактов.")

async def show_contact_card_from_search(message: Message, contact):
    """Показать карточку контакта из результатов поиска"""
    
    # Получаем статистику сообщений
    messages = db.get_contact_messages(contact.id, limit=100)
    incoming_count = len([m for m in messages if m.direction == "incoming"])
    outgoing_count = len([m for m in messages if m.direction == "outgoing"])
    
    card_text = (
        f"📇 Найденный контакт:\n\n"
        f"👤 <b>Имя:</b> {contact.name}\n"
        f"📱 <b>Телефон:</b> {contact.phone}\n"
        f"📝 <b>Примечание:</b> {contact.note or 'Не указано'}\n"
        f"🆔 <b>ID:</b> {contact.id}\n"
        f"📅 <b>Добавлен:</b> {contact.date_added.strftime('%d.%m.%Y %H:%M')}\n\n"
        f"📊 <b>Статистика:</b>\n"
        f"📨 Входящих: {incoming_count}\n"
        f"📤 Исходящих: {outgoing_count}\n"
        f"💬 Всего: {len(messages)}"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="📖 История", callback_data=f"history_{contact.id}")
    
    if contact.telegram_user_id:
        builder.button(text="💬 Написать", callback_data=f"send_to_{contact.id}")
        card_text += f"\n\n✅ <b>Telegram ID:</b> {contact.telegram_user_id}"
    else:
        builder.button(text="🔗 Установить Telegram ID", callback_data=f"set_telegram_id_{contact.id}")
        card_text += f"\n\n❌ <b>Telegram ID не установлен</b>"
    
    builder.button(text="🔍 Новый поиск", callback_data="search_contacts")
    builder.button(text="🏠 Главное меню", callback_data="main_menu")
    builder.adjust(2, 1, 1)
    
    await message.reply(card_text, reply_markup=builder.as_markup(), parse_mode="HTML")

# =================================================================
# 👥 ФУНКЦИИ УПРАВЛЕНИЯ АДМИНИСТРАТОРАМИ
# =================================================================

async def show_admin_menu(callback_query: CallbackQuery):
    """Показать меню управления администраторами"""
    
    # Только владелец может управлять админами
    if callback_query.from_user.id != Config.OWNER_ID:
        await callback_query.answer("⛔ Только владелец может управлять администраторами.", show_alert=True)
        return
    
    admins = db.get_all_admins()
    admin_count = len(admins)
    
    menu_text = (
        f"👥 Управление администраторами\n\n"
        f"📊 Всего администраторов: {admin_count}\n\n"
        f"Выберите действие:"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Список админов", callback_data="admin_list")
    builder.button(text="➕ Добавить админа", callback_data="admin_add")
    builder.button(text="➖ Удалить админа", callback_data="admin_remove")
    builder.button(text="⬅️ Назад", callback_data="main_menu")
    builder.adjust(1)
    
    await callback_query.message.edit_text(menu_text, reply_markup=builder.as_markup())

async def show_admin_list(callback_query: CallbackQuery):
    """Показать список администраторов"""
    
    admins = db.get_all_admins()
    
    if not admins:
        builder = InlineKeyboardBuilder()
        builder.button(text="⬅️ Назад", callback_data="admin_manage")
        
        await callback_query.message.edit_text(
            "📋 Список администраторов пуст.",
            reply_markup=builder.as_markup()
        )
        return
    
    admin_text = "📋 Список администраторов:\n\n"
    
    builder = InlineKeyboardBuilder()
    
    for i, admin in enumerate(admins, 1):
        status = "👑" if admin.telegram_user_id == Config.OWNER_ID else "🛡️"
        admin_text += (
            f"{i}. {status} @{admin.username}\n"
            f"🆔 ID: {admin.telegram_user_id}\n"
            f"📅 Добавлен: {admin.date_added.strftime('%d.%m.%Y')}\n\n"
        )
        
        if admin.telegram_user_id != Config.OWNER_ID:  # Нельзя удалить владельца
            builder.button(
                text=f"➖ {admin.username}",
                callback_data=f"remove_admin_{admin.telegram_user_id}"
            )
    
    builder.button(text="⬅️ Назад", callback_data="admin_manage")
    builder.adjust(1)
    
    await callback_query.message.edit_text(admin_text, reply_markup=builder.as_markup())

async def setup_bot_commands():
    """Настройка команд бота"""
    commands = [
        BotCommand(command="start", description="🏠 Главное меню"),
        BotCommand(command="add_admin", description="🛡️ Добавить администратора"),
        BotCommand(command="list_admins", description="📋 Список администраторов"),
    ]
    
    await bot.set_my_commands(commands)

async def main():
    """Основная функция запуска бота"""
    # Проверяем конфигурацию
    validation_errors = Config.validate_config()
    if validation_errors:
        print("❌ Ошибки конфигурации:")
        for error in validation_errors:
            print(f"  {error}")
        print("\nОткройте файл Config.py и исправьте ошибки.")
        return
    
    if Config.BOT_MODE != "bot":
        print("❌ Для этого скрипта установите BOT_MODE = 'bot' в Config.py")
        return
    
    print("🚀 Запуск Telegram CRM бота в режиме обычного бота...")
    
    # Инициализация базы данных
    db.init_db()
    
    # Очищаем дублированных админов
    deleted_count = db.remove_duplicate_admins()
    if deleted_count > 0:
        print(f"🧹 Очищено дублированных админов: {deleted_count}")
    
    # Инициализируем userbot для автоматического импорта контактов
    await init_userbot_for_contacts()
    
    # Настройка команд
    await setup_bot_commands()
    
    logger.info("🚀 Бот запущен в режиме обычного бота!")
    
    # Выводим информацию о конфигурации
    Config.print_config_info()
    
    print("\n✅ Бот готов к работе!")
    print("📱 Отправьте /start боту в Telegram для начала работы")
    
    # Запуск бота
    try:
        await dp.start_polling(bot, skip_updates=True)
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен пользователем.")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        logger.exception("Критическая ошибка при запуске")
    finally:
        if userbot_client:
            try:
                await userbot_client.disconnect()
                logger.info("🔌 Userbot отключен")
            except:
                pass
        await bot.session.close()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен пользователем.")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}") 