from telethon import events, Button
from loguru import logger
from typing import List, Optional
from database.db import Database
from database.models import Contact
from utils.telegram_contacts import TelegramContactsManager
import Config

class ContactHandler:
    def __init__(self, client, db: Database):
        self.client = client
        self.db = db
        self.telegram_contacts = TelegramContactsManager(client)
        self.setup_handlers()

    def setup_handlers(self):
        """Установка обработчиков для работы с контактами"""
        self.client.add_event_handler(
            self.handle_contacts_menu,
            events.CallbackQuery(pattern=b'contacts_menu')
        )
        self.client.add_event_handler(
            self.handle_add_contact,
            events.CallbackQuery(pattern=b'add_contact')
        )
        self.client.add_event_handler(
            self.handle_search_contact,
            events.CallbackQuery(pattern=b'search_contact')
        )
        self.client.add_event_handler(
            self.handle_add_to_telegram,
            events.CallbackQuery(pattern=b'add_to_telegram_')
        )

    async def get_contacts_keyboard(self) -> List[List[Button]]:
        """Создание клавиатуры для меню контактов"""
        return [
            [Button.inline("➕ Добавить контакт", b"add_contact")],
            [Button.inline("🔍 Поиск контакта", b"search_contact")],
            [Button.inline("📋 Список контактов", b"list_contacts")],
            [Button.inline("⬅️ Назад в главное меню", b"admin_menu")]
        ]

    async def handle_contacts_menu(self, event):
        """Обработка открытия меню контактов"""
        if not self.db.is_admin(event.sender_id):
            await event.answer("⛔ У вас нет прав администратора.", alert=True)
            return

        await event.edit(
            "📇 Меню управления контактами\n\n"
            "Выберите действие:",
            buttons=await self.get_contacts_keyboard()
        )

    async def handle_add_contact(self, event):
        """Обработка добавления нового контакта"""
        if not self.db.is_admin(event.sender_id):
            await event.answer("⛔ У вас нет прав администратора.", alert=True)
            return

        # Переводим пользователя в режим добавления контакта
        await event.edit(
            "👤 Добавление нового контакта\n\n"
            "Пожалуйста, отправьте контакт в формате:\n"
            "Имя\nТелефон\nПримечание (опционально)"
        )
        
        # Добавляем временный обработчик для получения данных контакта
        @self.client.on(events.NewMessage(from_users=event.sender_id))
        async def contact_data_handler(msg_event):
            try:
                # Парсим данные контакта
                lines = msg_event.text.split('\n')
                if len(lines) < 2:
                    await msg_event.reply(
                        "❌ Неверный формат!\n"
                        "Пожалуйста, отправьте данные в формате:\n"
                        "Имя\nТелефон\nПримечание (опционально)"
                    )
                    return

                name = lines[0].strip()
                phone = lines[1].strip()
                note = lines[2].strip() if len(lines) > 2 else None

                # Добавляем контакт в базу
                contact_id = self.db.add_contact(name, phone, note)
                
                # Автоматически добавляем контакт в Telegram (если включено)
                telegram_result = None
                if Config.AUTO_IMPORT_TO_TELEGRAM:
                    try:
                        telegram_result = await self.telegram_contacts.add_contact_to_telegram(name, phone)
                        
                        if telegram_result["success"]:
                            # Обновляем информацию в базе
                            self.db.update_contact_telegram_id(contact_id, telegram_result["user_id"])
                            logger.info(f"📱 Контакт автоматически добавлен в Telegram: {name}")
                        
                    except Exception as e:
                        logger.warning(f"Не удалось автоматически добавить контакт в Telegram: {e}")

                # Формируем ответное сообщение
                response_text = (
                    f"✅ Контакт успешно добавлен!\n\n"
                    f"👤 Имя: {name}\n"
                    f"📱 Телефон: {phone}\n"
                    f"📝 Примечание: {note if note else '-'}\n"
                )
                
                # Добавляем информацию о Telegram
                if telegram_result:
                    if telegram_result["success"]:
                        username_info = f" (@{telegram_result['username']})" if telegram_result["username"] else ""
                        response_text += f"\n📲 Telegram: Добавлен{username_info}"
                    else:
                        response_text += f"\n⚠️ Telegram: {telegram_result['message']}"

                await msg_event.reply(response_text)

                # Возвращаем меню контактов
                await msg_event.respond(
                    "📇 Меню управления контактами",
                    buttons=await self.get_contacts_keyboard()
                )

                # Удаляем временный обработчик
                self.client.remove_event_handler(contact_data_handler)

            except Exception as e:
                logger.error(f"Ошибка при добавлении контакта: {e}")
                await msg_event.reply("❌ Произошла ошибка при добавлении контакта.")

    async def handle_search_contact(self, event):
        """Обработка поиска контактов"""
        if not self.db.is_admin(event.sender_id):
            await event.answer("⛔ У вас нет прав администратора.", alert=True)
            return

        await event.edit(
            "🔍 Поиск контактов\n\n"
            "Введите имя или номер телефона для поиска:"
        )

        @self.client.on(events.NewMessage(from_users=event.sender_id))
        async def search_handler(msg_event):
            try:
                query = msg_event.text.strip()
                contacts = self.db.search_contacts(query)

                if not contacts:
                    await msg_event.reply(
                        "❌ Контакты не найдены.",
                        buttons=await self.get_contacts_keyboard()
                    )
                    return

                # Формируем список найденных контактов
                result = "🔍 Результаты поиска:\n\n"
                for contact in contacts:
                    result += (
                        f"👤 {contact.name}\n"
                        f"📱 {contact.phone}\n"
                        f"📝 {contact.note if contact.note else '-'}\n"
                        f"➖➖➖➖➖➖\n"
                    )

                await msg_event.reply(
                    result,
                    buttons=[[Button.inline(f"✏️ Редактировать {contact.name}", 
                             f"edit_contact_{contact.id}".encode())] for contact in contacts] +
                            [[Button.inline("⬅️ Назад", b"contacts_menu")]]
                )

                # Удаляем временный обработчик
                self.client.remove_event_handler(search_handler)

            except Exception as e:
                logger.error(f"Ошибка при поиске контактов: {e}")
                await msg_event.reply("❌ Произошла ошибка при поиске контактов.")

    async def handle_add_to_telegram(self, event):
        """Обработка ручного добавления контакта в Telegram"""
        if not Config.is_admin(event.sender_id) and not self.db.is_admin(event.sender_id):
            await event.answer("⛔ У вас нет прав администратора.", alert=True)
            return

        try:
            # Извлекаем ID контакта из callback_data
            contact_id = int(event.data.decode().split('_')[-1])
            contact = self.db.get_contact(contact_id)
            
            if not contact:
                await event.answer("❌ Контакт не найден.", alert=True)
                return

            await event.answer("📱 Добавляю контакт в Telegram...", alert=False)
            
            # Добавляем контакт в Telegram
            result = await self.telegram_contacts.add_contact_to_telegram(contact.name, contact.phone)
            
            if result["success"]:
                # Обновляем информацию в базе
                self.db.update_contact_telegram_id(contact_id, result["user_id"])
                
                username_info = f" (@{result['username']})" if result["username"] else ""
                await event.edit(
                    f"✅ Контакт добавлен в Telegram!\n\n"
                    f"👤 {contact.name}\n"
                    f"📱 {contact.phone}\n"
                    f"📲 Telegram ID: {result['user_id']}{username_info}",
                    buttons=[[Button.inline("⬅️ Назад к контактам", b"contacts_menu")]]
                )
            else:
                await event.edit(
                    f"❌ Не удалось добавить контакт в Telegram\n\n"
                    f"👤 {contact.name}\n"
                    f"📱 {contact.phone}\n"
                    f"⚠️ Причина: {result['message']}",
                    buttons=[[Button.inline("⬅️ Назад к контактам", b"contacts_menu")]]
                )
                
        except Exception as e:
            logger.error(f"Ошибка при добавлении контакта в Telegram: {e}")
            await event.answer("❌ Произошла ошибка при добавлении контакта.", alert=True) 