from telethon import events, Button
from loguru import logger
from typing import List
from database.db import Database
import Config

class AdminHandler:
    def __init__(self, client, db: Database):
        self.client = client
        self.db = db
        self.setup_handlers()

    def setup_handlers(self):
        """Установка обработчиков команд администратора"""
        self.client.add_event_handler(
            self.handle_start,
            events.NewMessage(pattern='/start')
        )
        self.client.add_event_handler(
            self.handle_add_admin,
            events.NewMessage(pattern='/add_admin')
        )
        self.client.add_event_handler(
            self.handle_remove_admin,
            events.NewMessage(pattern='/remove_admin')
        )
        self.client.add_event_handler(
            self.handle_list_admins,
            events.NewMessage(pattern='/list_admins')
        )
        self.client.add_event_handler(
            self.handle_admin_menu,
            events.CallbackQuery(pattern=b'admin_menu')
        )
        self.client.add_event_handler(
            self.handle_statistics,
            events.CallbackQuery(pattern=b'statistics')
        )

    async def get_admin_keyboard(self) -> List[List[Button]]:
        """Создание клавиатуры для админ-меню"""
        return [
            [Button.inline("📇 Контакты", b"contacts_menu")],
            [Button.inline("📨 Отправить сообщение", b"send_message")],
            [Button.inline("🗂️ История переписки", b"message_history")],
            [Button.inline("🔍 Поиск", b"search_menu")],
            [Button.inline("📋 Управление админами", b"manage_admins")],
            [Button.inline("📊 Статистика", b"statistics")],
            [Button.inline("⚙️ Настройки", b"settings")]
        ]

    async def handle_start(self, event):
        """Обработка команды /start"""
        sender = await event.get_sender()
        
        # Проверяем права доступа через Config
        if not Config.is_admin(sender.id) and not self.db.is_admin(sender.id):
            await event.reply("⛔ У вас нет прав администратора.")
            return

        await event.reply(
            "👋 Добро пожаловать в админ-панель CRM!\n\n"
            "Выберите действие из меню ниже:",
            buttons=await self.get_admin_keyboard()
        )

    async def handle_add_admin(self, event):
        """Обработка команды /add_admin"""
        sender = await event.get_sender()
        if not self.db.is_admin(sender.id):
            await event.reply("⛔ У вас нет прав для добавления администраторов.")
            return

        try:
            # Получаем username нового админа из сообщения
            args = event.text.split()
            if len(args) != 2:
                await event.reply("❌ Использование: /add_admin @username")
                return

            username = args[1].replace("@", "")
            # Получаем информацию о пользователе
            user = await self.client.get_entity(username)
            
            # Проверяем, не является ли уже админом
            if self.db.is_admin(user.id):
                await event.reply(f"⚠️ Пользователь @{username} уже является администратором!")
                return
            
            # Добавляем нового админа
            self.db.add_admin(username, user.id)
            await event.reply(f"✅ Пользователь @{username} успешно добавлен как администратор!")
            
        except Exception as e:
            logger.error(f"Ошибка при добавлении админа: {e}")
            await event.reply("❌ Ошибка при добавлении администратора. Проверьте правильность username.")

    async def handle_remove_admin(self, event):
        """Обработка команды /remove_admin"""
        sender = await event.get_sender()
        if not self.db.is_admin(sender.id):
            await event.reply("⛔ У вас нет прав для удаления администраторов.")
            return

        try:
            args = event.text.split()
            if len(args) != 2:
                await event.reply("❌ Использование: /remove_admin @username")
                return

            username = args[1].replace("@", "")
            user = await self.client.get_entity(username)
            
            if not self.db.is_admin(user.id):
                await event.reply(f"⚠️ Пользователь @{username} не является администратором!")
                return
            
            self.db.remove_admin(user.id)
            await event.reply(f"✅ Пользователь @{username} удален из администраторов!")
            
        except Exception as e:
            logger.error(f"Ошибка при удалении админа: {e}")
            await event.reply("❌ Ошибка при удалении администратора.")

    async def handle_list_admins(self, event):
        """Обработка команды /list_admins"""
        sender = await event.get_sender()
        if not self.db.is_admin(sender.id):
            await event.reply("⛔ У вас нет прав для просмотра списка администраторов.")
            return

        try:
            admins = self.db.get_all_admins()
            if not admins:
                await event.reply("📋 Список администраторов пуст.")
                return

            message = "📋 Список администраторов:\n\n"
            for i, admin in enumerate(admins, 1):
                message += f"{i}. @{admin.username} (ID: {admin.telegram_user_id})\n"

            await event.reply(message)
            
        except Exception as e:
            logger.error(f"Ошибка при получении списка админов: {e}")
            await event.reply("❌ Ошибка при получении списка администраторов.")

    async def handle_statistics(self, event):
        """Обработка показа статистики"""
        sender = await event.get_sender()
        if not self.db.is_admin(sender.id):
            await event.answer("⛔ У вас нет прав администратора.", alert=True)
            return

        try:
            # Собираем статистику
            contacts_count = self.db.get_contacts_count()
            messages_total = self.db.get_messages_count()
            messages_today = self.db.get_messages_count_by_period(1)
            messages_week = self.db.get_messages_count_by_period(7)
            admins_count = len(self.db.get_all_admins())

            stats_text = (
                "📊 Статистика CRM системы\n\n"
                f"👥 Контактов в базе: {contacts_count}\n"
                f"💬 Всего сообщений: {messages_total}\n"
                f"📅 Сообщений сегодня: {messages_today}\n"
                f"📈 Сообщений за неделю: {messages_week}\n"
                f"🛡️ Администраторов: {admins_count}"
            )

            await event.edit(
                stats_text,
                buttons=[[Button.inline("⬅️ Назад в главное меню", b"admin_menu")]]
            )

        except Exception as e:
            logger.error(f"Ошибка при получении статистики: {e}")
            await event.answer("❌ Ошибка при получении статистики.", alert=True)

    async def handle_admin_menu(self, event):
        """Обработка нажатий на кнопки админ-меню"""
        sender = await event.get_sender()
        if not self.db.is_admin(sender.id):
            await event.answer("⛔ У вас нет прав администратора.", alert=True)
            return

        await event.edit(
            "👋 Добро пожаловать в админ-панель CRM!\n\n"
            "Выберите действие из меню ниже:",
            buttons=await self.get_admin_keyboard()
        ) 