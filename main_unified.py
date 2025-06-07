import asyncio
import logging
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, F, BaseMiddleware
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, BotCommand, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from telethon import TelegramClient, events
from telethon.tl.functions.contacts import ImportContactsRequest
from telethon.tl.types import InputPhoneContact
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from loguru import logger

import Config
from database.db import Database
from utils.date_helpers import format_date_display

# Настройка логирования
logger.remove()
logger.add(
    "logs/crm_unified.log",
    rotation="10 MB",
    retention="30 days",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} - {message}",
    level="INFO"
)

# Инициализация
db = Database()
bot = Bot(token=Config.BOT_TOKEN)
dp = Dispatcher()

# Глобальные переменные
userbot_client = None
telegram_contacts_manager = None
user_states = {}
user_search_states = {}
user_message_states = {}
user_reply_states = {}

class TelegramContactsManager:
    """Менеджер для работы с контактами Telegram через userbot"""
    
    def __init__(self, client):
        self.client = client

    async def add_contact_to_telegram(self, name: str, phone: str):
        """Добавить контакт в Telegram и получить его user_id"""
        try:
            # Создаем контакт
            contact = InputPhoneContact(
                client_id=0,
                phone=phone,
                first_name=name,
                last_name=""
            )
            
            # Импортируем контакт
            result = await self.client(ImportContactsRequest([contact]))
            
            if result.users:
                user = result.users[0]
                return {
                    "success": True,
                    "user_id": user.id,
                    "username": user.username,
                    "message": f"Контакт {name} добавлен в Telegram"
                }
            else:
                return {
                    "success": False,
                    "user_id": None,
                    "username": None,
                    "message": "Пользователь не найден в Telegram"
                }
                
        except Exception as e:
            logger.error(f"Ошибка при добавлении контакта в Telegram: {e}")
            return {
                "success": False,
                "user_id": None,
                "username": None,
                "message": f"Ошибка: {str(e)}"
            }

async def init_userbot():
    """Инициализация userbot клиента"""
    global userbot_client, telegram_contacts_manager
    
    logger.info("🔄 Инициализация userbot...")
    
    try:
        userbot_client = TelegramClient(
            'telegram_crm_session',
            Config.API_ID,
            Config.API_HASH,
            device_model="Telegram CRM",
            system_version="1.0.0",
            app_version="1.0.0",
            lang_code="ru",
            system_lang_code="ru"
        )
        
        await userbot_client.start(phone=Config.PHONE_NUMBER)
        
        # Инициализация менеджера контактов
        telegram_contacts_manager = TelegramContactsManager(userbot_client)
        
        # Обработчик входящих сообщений
        @userbot_client.on(events.NewMessage)
        async def handle_userbot_message(event):
            await process_userbot_incoming_message(event)
        
        logger.info("✅ Userbot инициализирован")
        
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации userbot: {e}")
        userbot_client = None

async def process_userbot_incoming_message(event):
    """Обработка входящих сообщений через userbot"""
    try:
        sender = await event.get_sender()
        
        # Пропускаем сообщения от ботов и самого себя
        if sender.bot or sender.id == (await userbot_client.get_me()).id:
            return
        
        # Пропускаем сообщения от нашего бота
        if sender.id == int(Config.BOT_TOKEN.split(':')[0]):
            return
            
        sender_name = f"{sender.first_name or ''} {sender.last_name or ''}".strip()
        if not sender_name:
            sender_name = sender.username or "Неизвестный"
        
        logger.info(f"📨 Сообщение от: {sender_name} (ID: {sender.id})")
        
        # Ищем контакт в базе данных
        contact = db.get_contact_by_telegram_id(sender.id)
        
        if not contact:
            # Создаем новый контакт
            phone = f"+{sender.id}"  # Временный номер
            note = f"Telegram: @{sender.username}" if sender.username else "Автоматически создан"
            
            contact_id = db.add_contact(sender_name, phone, note)
            db.update_contact_telegram_id(contact_id, sender.id)
            contact = db.get_contact(contact_id)
            
            logger.info(f"📇 Создан новый контакт: {sender_name}")
        
        # Сохраняем сообщение
        db.add_message(
            contact_id=contact.id,
            message_id=event.message.id,
            direction="incoming",
            text=event.message.text or "[Медиа]"
        )
        
        # Уведомляем админов
        await notify_admins_about_incoming_message(contact, event.message, sender)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке входящего сообщения: {e}")

async def notify_admins_about_incoming_message(contact, message, sender):
    """Уведомление администраторов о новом сообщении"""
    
    admins = db.get_all_admins()
    
    if not admins:
        return
    
    notification_text = (
        f"📨 Новое входящее сообщение!\n\n"
        f"👤 {contact.name}\n"
        f"📱 {contact.phone}\n"
        f"🆔 Контакт ID: {contact.id}\n"
        f"📝 Примечание: {contact.note or '-'}\n\n"
        f"💬 Сообщение:\n"
        f"{message.text or '[Медиа файл]'}\n\n"
        f"⏰ {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="💬 Ответить", callback_data=f"reply_{contact.id}")
    builder.button(text="📖 История", callback_data=f"history_{contact.id}")
    builder.button(text="📇 Карточка", callback_data=f"view_contact_{contact.id}")
    builder.adjust(1)
    
    for admin in admins:
        try:
            await bot.send_message(
                chat_id=admin.telegram_user_id,
                text=notification_text,
                reply_markup=builder.as_markup()
            )
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления админу {admin.username}: {e}")

class BotHandlers:
    """Класс с обработчиками бота"""
    
    @staticmethod
    def get_main_keyboard():
        """Главная клавиатура"""
        builder = InlineKeyboardBuilder()
        builder.button(text="📇 Контакты", callback_data="contacts_menu")
        builder.button(text="📨 Отправить сообщение", callback_data="message_send")
        builder.button(text="🗂️ История переписки", callback_data="history_view")
        builder.button(text="🔍 Поиск контактов", callback_data="search_contacts")
        builder.button(text="👥 Администраторы", callback_data="admin_manage")
        builder.button(text="📊 Статистика", callback_data="stats_view")
        builder.adjust(2, 2, 2)
        return builder.as_markup()
    
    @staticmethod
    def get_contacts_keyboard():
        """Клавиатура для работы с контактами"""
        builder = InlineKeyboardBuilder()
        builder.button(text="➕ Добавить контакт", callback_data="contacts_add")
        builder.button(text="📋 Список контактов", callback_data="contacts_list")
        builder.button(text="🔍 Поиск контакта", callback_data="search_contacts")
        builder.button(text="⬅️ Назад", callback_data="main_menu")
        builder.adjust(1)
        return builder.as_markup()
    
    @staticmethod
    def is_admin(user_id: int) -> bool:
        """Проверка прав администратора"""
        return user_id == Config.OWNER_ID or db.is_admin(user_id)

# =================================================================
# 🎯 КОМАНДЫ БОТА
# =================================================================

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обработка команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username or "unknown"
    full_name = message.from_user.full_name or "Неизвестный пользователь"
    
    # Устанавливаем владельца при первом запуске
    if not Config.OWNER_ID:
        Config.OWNER_ID = user_id
        db.set_owner(user_id, username)
        logger.info(f"👑 Владелец установлен: {full_name} (ID: {user_id})")
    
    # Проверяем права администратора
    if not BotHandlers.is_admin(user_id):
        await message.reply(
            "⛔ У вас нет прав доступа к этой системе.\n"
            "Обратитесь к администратору."
        )
        return
    
    # Добавляем владельца как админа (если еще не добавлен)
    if user_id == Config.OWNER_ID and not db.is_admin(user_id):
        db.add_admin(username, user_id)
    
    welcome_text = (
        f"👋 Добро пожаловать в CRM систему, {full_name}!\n\n"
        f"🏠 Главное меню\n\n"
        f"Выберите действие:"
    )
    
    await message.reply(welcome_text, reply_markup=BotHandlers.get_main_keyboard())

@dp.message(Command("add_admin"))
async def cmd_add_admin(message: Message):
    """Добавление администратора"""
    user_id = message.from_user.id
    
    # Только владелец может добавлять админов
    if user_id != Config.OWNER_ID:
        await message.reply("⛔ Только владелец может добавлять администраторов.")
        return
    
    try:
        args = message.text.split()
        if len(args) != 2:
            await message.reply(
                "❌ Неверный формат команды.\n"
                "Используйте: /add_admin USER_ID\n"
                "Где USER_ID - Telegram ID пользователя"
            )
            return
        
        admin_id = int(args[1])
        
        if db.is_admin(admin_id):
            await message.reply("⚠️ Пользователь уже является администратором.")
            return
        
        # Получаем информацию о пользователе (здесь можно добавить логику получения username)
        username = f"user_{admin_id}"  # Временное решение
        
        db.add_admin(username, admin_id)
        Config.ADMIN_IDS.append(admin_id)
        
        await message.reply(f"✅ Администратор добавлен: {username} (ID: {admin_id})")
        
    except ValueError:
        await message.reply("❌ USER_ID должен быть числом.")
    except Exception as e:
        logger.error(f"Ошибка при добавлении админа: {e}")
        await message.reply("❌ Ошибка при добавлении администратора.")

# =================================================================
# 📞 ОБРАБОТЧИКИ CALLBACK'ОВ
# =================================================================

@dp.callback_query(F.data.startswith(("main_", "contacts_", "message_", "history_", "search_", "admin_", "stats_")))
async def process_main_callbacks(callback_query: CallbackQuery):
    """Обработка основных callback'ов"""
    
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    if not BotHandlers.is_admin(user_id):
        await callback_query.answer("⛔ У вас нет прав администратора.", show_alert=True)
        return
    
    try:
        if data == "main_menu":
            await callback_query.message.edit_text(
                "🏠 Главное меню CRM системы\n\nВыберите действие:",
                reply_markup=BotHandlers.get_main_keyboard()
            )
        
        elif data == "contacts_menu":
            await callback_query.message.edit_text(
                "📇 Управление контактами\n\nВыберите действие:",
                reply_markup=BotHandlers.get_contacts_keyboard()
            )
        
        elif data == "contacts_add":
            user_states[user_id] = "adding_contact"
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
            await show_contacts_list(callback_query)
        
        elif data == "message_send":
            await show_send_message_menu(callback_query)
        
        elif data == "history_view":
            await show_history_menu(callback_query)
        
        elif data == "search_contacts":
            await show_search_menu(callback_query)
        
        elif data == "admin_manage":
            await show_admin_menu(callback_query)
        
        elif data == "stats_view":
            await show_stats(callback_query)
        
        else:
            await callback_query.answer("🚧 Функция в разработке", show_alert=True)
    
    except Exception as e:
        logger.error(f"Ошибка при обработке callback: {e}")
        await callback_query.answer("❌ Произошла ошибка.", show_alert=True)
    
    await callback_query.answer()

# =================================================================
# 📇 ФУНКЦИИ РАБОТЫ С КОНТАКТАМИ
# =================================================================

async def show_contacts_list(callback_query: CallbackQuery, page: int = 0):
    """Показать список контактов"""
    
    offset = page * Config.CONTACTS_PER_PAGE
    contacts = db.get_all_contacts(limit=Config.CONTACTS_PER_PAGE, offset=offset)
    
    if not contacts:
        builder = InlineKeyboardBuilder()
        builder.button(text="⬅️ Назад", callback_data="contacts_menu")
        
        await callback_query.message.edit_text(
            "📋 Список контактов пуст.",
            reply_markup=builder.as_markup()
        )
        return
    
    contact_text = f"📋 Список контактов (стр. {page + 1}):\n\n"
    
    builder = InlineKeyboardBuilder()
    
    for contact in contacts:
        telegram_status = "✅" if contact.telegram_user_id else "❌"
        contact_text += (
            f"👤 {contact.name}\n"
            f"📱 {contact.phone}\n"
            f"📝 {contact.note or '-'}\n"
            f"💬 Telegram: {telegram_status}\n"
            f"➖➖➖➖➖\n"
        )
        
        builder.button(
            text=f"📇 {contact.name}",
            callback_data=f"view_contact_{contact.id}"
        )
    
    # Навигация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"contacts_page_{page-1}"))
    
    next_contacts = db.get_all_contacts(limit=1, offset=(page + 1) * Config.CONTACTS_PER_PAGE)
    if next_contacts:
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"contacts_page_{page+1}"))
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    builder.button(text="⬅️ Назад", callback_data="contacts_menu")
    builder.adjust(1)
    
    await callback_query.message.edit_text(contact_text, reply_markup=builder.as_markup())

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
    builder.button(text="⬅️ Назад", callback_data="main_menu")
    builder.adjust(1)
    
    await callback_query.message.edit_text(menu_text, reply_markup=builder.as_markup())

# =================================================================
# 🗂️ ФУНКЦИИ ИСТОРИИ
# =================================================================

async def show_history_menu(callback_query: CallbackQuery):
    """Показать меню истории переписки"""
    
    menu_text = (
        "🗂️ История переписки\n\n"
        "Выберите контакт для просмотра истории:"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="📇 По контакту", callback_data="history_by_contact")
    builder.button(text="⬅️ Назад", callback_data="main_menu")
    builder.adjust(1)
    
    await callback_query.message.edit_text(menu_text, reply_markup=builder.as_markup())

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
    
    user_search_states[callback_query.from_user.id] = True
    
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="main_menu")
    
    await callback_query.message.edit_text(menu_text, reply_markup=builder.as_markup())

# =================================================================
# 👥 ФУНКЦИИ УПРАВЛЕНИЯ АДМИНАМИ
# =================================================================

async def show_admin_menu(callback_query: CallbackQuery):
    """Показать меню управления администраторами"""
    
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
    builder.button(text="⬅️ Назад", callback_data="main_menu")
    builder.adjust(1)
    
    await callback_query.message.edit_text(menu_text, reply_markup=builder.as_markup())

# =================================================================
# 📊 ФУНКЦИИ СТАТИСТИКИ
# =================================================================

async def show_stats(callback_query: CallbackQuery):
    """Показать статистику"""
    
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

# =================================================================
# 💬 ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ
# =================================================================

@dp.message(F.text)
async def handle_text_messages(message: Message):
    """Обработка текстовых сообщений"""
    
    user_id = message.from_user.id
    
    if not BotHandlers.is_admin(user_id):
        return
    
    # Обработка добавления контакта
    if user_id in user_states and user_states[user_id] == "adding_contact":
        await process_adding_contact(message)
        return
    
    # Обработка поиска
    if user_id in user_search_states and user_search_states[user_id]:
        await process_search(message)
        return
    
    # Обработка отправки сообщения
    if user_id in user_message_states:
        contact_id = user_message_states[user_id]
        await send_message_to_contact(message, contact_id)
        return
    
    # Обработка ответа на сообщение
    if user_id in user_reply_states:
        contact_id = user_reply_states[user_id]
        await send_reply_to_contact(message, contact_id)
        return

async def process_adding_contact(message: Message):
    """Обработка добавления контакта"""
    
    user_id = message.from_user.id
    
    try:
        lines = message.text.strip().split('\n')
        
        if len(lines) < 2:
            await message.reply(
                "❌ Неверный формат.\n"
                "Укажите минимум имя и телефон."
            )
            return
        
        name = lines[0].strip()
        phone = lines[1].strip()
        note = lines[2].strip() if len(lines) > 2 else None
        
        # Добавляем контакт в базу
        contact_id = db.add_contact(name, phone, note)
        
        # Пытаемся добавить в Telegram
        telegram_result = None
        if telegram_contacts_manager:
            try:
                telegram_result = await telegram_contacts_manager.add_contact_to_telegram(name, phone)
                if telegram_result["success"]:
                    db.update_contact_telegram_id(contact_id, telegram_result["user_id"])
            except Exception as e:
                logger.error(f"Ошибка при добавлении в Telegram: {e}")
        
        # Формируем ответ
        success_text = f"✅ Контакт успешно добавлен!\n\n👤 {name}\n📱 {phone}\n"
        
        if note:
            success_text += f"📝 {note}\n"
        
        if telegram_result and telegram_result["success"]:
            username_info = f" (@{telegram_result['username']})" if telegram_result["username"] else ""
            success_text += f"✅ Telegram ID: {telegram_result['user_id']}{username_info}"
        else:
            success_text += "❌ Telegram ID не установлен"
        
        builder = InlineKeyboardBuilder()
        builder.button(text="🏠 Главное меню", callback_data="main_menu")
        builder.button(text="📇 Контакты", callback_data="contacts_menu")
        builder.adjust(1)
        
        await message.reply(success_text, reply_markup=builder.as_markup())
        
        # Сбрасываем состояние
        del user_states[user_id]
        
    except Exception as e:
        logger.error(f"Ошибка при добавлении контакта: {e}")
        await message.reply("❌ Ошибка при добавлении контакта.")

async def process_search(message: Message):
    """Обработка поиска контактов"""
    
    user_id = message.from_user.id
    query = message.text.strip()
    
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
        else:
            result_text = f"🔍 Результаты поиска '{query}' ({len(contacts)} найдено):\n\n"
            
            builder = InlineKeyboardBuilder()
            
            for contact in contacts[:10]:  # Показываем максимум 10 результатов
                telegram_status = "✅" if contact.telegram_user_id else "❌"
                result_text += (
                    f"👤 {contact.name}\n"
                    f"📱 {contact.phone}\n"
                    f"📝 {contact.note or '-'}\n"
                    f"💬 Telegram: {telegram_status}\n"
                    f"➖➖➖➖➖\n"
                )
                
                builder.button(
                    text=f"📇 {contact.name}",
                    callback_data=f"view_contact_{contact.id}"
                )
            
            if len(contacts) > 10:
                result_text += f"... и еще {len(contacts) - 10} контактов"
            
            builder.button(text="🔍 Новый поиск", callback_data="search_contacts")
            builder.button(text="🏠 Главное меню", callback_data="main_menu")
            builder.adjust(2, 2, 1)
            
            await message.reply(result_text, reply_markup=builder.as_markup())
        
        # Сбрасываем состояние
        user_search_states[user_id] = False
        
    except Exception as e:
        logger.error(f"Ошибка при поиске: {e}")
        await message.reply("❌ Ошибка при поиске контактов.")

async def send_message_to_contact(message: Message, contact_id: int):
    """Отправка сообщения контакту через userbot"""
    
    user_id = message.from_user.id
    
    try:
        contact = db.get_contact(contact_id)
        if not contact:
            await message.reply("❌ Контакт не найден.")
            return
        
        if not contact.telegram_user_id:
            await message.reply("❌ У контакта не установлен Telegram ID.")
            return
        
        if not userbot_client:
            await message.reply("❌ Userbot не подключен.")
            return
        
        # Отправляем сообщение через userbot
        await userbot_client.send_message(contact.telegram_user_id, message.text)
        
        # Сохраняем в базу
        db.add_message(
            contact_id=contact_id,
            message_id=0,  # Временное значение
            direction="outgoing",
            text=message.text
        )
        
        await message.reply(
            f"✅ Сообщение отправлено контакту {contact.name}",
            reply_markup=InlineKeyboardBuilder().button(
                text="🏠 Главное меню", callback_data="main_menu"
            ).as_markup()
        )
        
        # Сбрасываем состояние
        del user_message_states[user_id]
        
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения: {e}")
        await message.reply("❌ Ошибка при отправке сообщения.")

async def send_reply_to_contact(message: Message, contact_id: int):
    """Отправка ответа контакту"""
    
    user_id = message.from_user.id
    
    try:
        contact = db.get_contact(contact_id)
        if not contact:
            await message.reply("❌ Контакт не найден.")
            return
        
        if not contact.telegram_user_id:
            await message.reply("❌ У контакта не установлен Telegram ID.")
            return
        
        if not userbot_client:
            await message.reply("❌ Userbot не подключен.")
            return
        
        # Отправляем ответ через userbot
        await userbot_client.send_message(contact.telegram_user_id, message.text)
        
        # Сохраняем в базу
        db.add_message(
            contact_id=contact_id,
            message_id=0,
            direction="outgoing", 
            text=message.text
        )
        
        await message.reply(
            f"✅ Ответ отправлен контакту {contact.name}",
            reply_markup=InlineKeyboardBuilder().button(
                text="🏠 Главное меню", callback_data="main_menu"
            ).as_markup()
        )
        
        # Сбрасываем состояние
        del user_reply_states[user_id]
        
    except Exception as e:
        logger.error(f"Ошибка при отправке ответа: {e}")
        await message.reply("❌ Ошибка при отправке ответа.")

# =================================================================
# 🚀 ЗАПУСК СИСТЕМЫ
# =================================================================

async def setup_bot_commands():
    """Настройка команд бота"""
    commands = [
        BotCommand(command="start", description="🏠 Главное меню"),
        BotCommand(command="add_admin", description="🛡️ Добавить администратора"),
    ]
    
    await bot.set_my_commands(commands)

async def main():
    """Основная функция запуска"""
    # Проверяем конфигурацию
    validation_errors = Config.validate_config()
    if validation_errors:
        print("❌ Ошибки конфигурации:")
        for error in validation_errors:
            print(f"  {error}")
        print("\nОткройте файл Config.py и исправьте ошибки.")
        return
    
    print("🚀 Запуск объединенной Telegram CRM системы...")
    
    # Инициализация базы данных
    db.init_db()
    
    # Очищаем дублированных админов
    deleted_count = db.remove_duplicate_admins()
    if deleted_count > 0:
        print(f"🧹 Очищено дублированных админов: {deleted_count}")
    
    # Инициализируем userbot
    await init_userbot()
    
    # Настройка команд
    await setup_bot_commands()
    
    logger.info("🚀 Объединенная CRM система запущена!")
    
    # Выводим информацию о конфигурации
    Config.print_config_info()
    
    print("\n✅ Система готова к работе!")
    print("📱 Отправьте /start боту в Telegram для начала работы")
    
    # Запуск бота
    try:
        await dp.start_polling(bot, skip_updates=True)
    except KeyboardInterrupt:
        print("\n👋 Система остановлена пользователем.")
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
        print("\n👋 Система остановлена пользователем.")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")