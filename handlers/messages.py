from telethon import events, Button
from loguru import logger
from typing import List, Optional
from database.db import Database
from database.models import Contact, Message

class MessageHandler:
    def __init__(self, client, db: Database):
        self.client = client
        self.db = db
        self.setup_handlers()

    def setup_handlers(self):
        """Установка обработчиков для работы с сообщениями"""
        self.client.add_event_handler(
            self.handle_send_message_menu,
            events.CallbackQuery(pattern=b'send_message')
        )
        self.client.add_event_handler(
            self.handle_message_history,
            events.CallbackQuery(pattern=b'message_history')
        )
        # Обработчик входящих сообщений
        self.client.add_event_handler(
            self.handle_incoming_message,
            events.NewMessage(incoming=True)
        )

    async def handle_send_message_menu(self, event):
        """Обработка меню отправки сообщений"""
        if not self.db.is_admin(event.sender_id):
            await event.answer("⛔ У вас нет прав администратора.", alert=True)
            return

        await event.edit(
            "📨 Отправка сообщения\n\n"
            "Выберите способ отправки:",
            buttons=[
                [Button.inline("📇 Выбрать из контактов", b"select_contact_for_message")],
                [Button.inline("📱 Ввести номер телефона", b"enter_phone_for_message")],
                [Button.inline("⬅️ Назад в главное меню", b"admin_menu")]
            ]
        )

    async def handle_select_contact_for_message(self, event):
        """Обработка выбора контакта для отправки сообщения"""
        if not self.db.is_admin(event.sender_id):
            await event.answer("⛔ У вас нет прав администратора.", alert=True)
            return

        # Получаем список последних контактов
        contacts = self.db.get_recent_contacts(limit=10)
        
        buttons = []
        for contact in contacts:
            buttons.append([Button.inline(
                f"👤 {contact.name} | 📱 {contact.phone}",
                f"send_to_contact_{contact.id}".encode()
            )])
        
        buttons.append([Button.inline("🔍 Поиск контакта", b"search_contact_for_message")])
        buttons.append([Button.inline("⬅️ Назад", b"send_message")])

        await event.edit(
            "📇 Выберите контакт для отправки сообщения:",
            buttons=buttons
        )

    async def handle_enter_phone_for_message(self, event):
        """Обработка ввода номера телефона для отправки сообщения"""
        if not self.db.is_admin(event.sender_id):
            await event.answer("⛔ У вас нет прав администратора.", alert=True)
            return

        await event.edit(
            "📱 Введите номер телефона для отправки сообщения:\n"
            "Формат: +7XXXXXXXXXX"
        )

        @self.client.on(events.NewMessage(from_users=event.sender_id))
        async def phone_handler(msg_event):
            try:
                phone = msg_event.text.strip()
                
                # Проверяем формат номера
                if not phone.startswith('+') or not phone[1:].isdigit():
                    await msg_event.reply(
                        "❌ Неверный формат номера!\n"
                        "Используйте формат: +7XXXXXXXXXX"
                    )
                    return

                # Проверяем, есть ли контакт в базе
                contact = self.db.get_contact_by_phone(phone)
                if not contact:
                    # Предлагаем создать новый контакт
                    await msg_event.reply(
                        "❓ Контакт не найден в базе. Создать новый?",
                        buttons=[
                            [Button.inline("✅ Да, создать", f"create_contact_{phone}".encode())],
                            [Button.inline("❌ Нет, отмена", b"send_message")]
                        ]
                    )
                else:
                    # Переходим к отправке сообщения
                    await self.prepare_message_sending(msg_event, contact)

                # Удаляем временный обработчик
                self.client.remove_event_handler(phone_handler)

            except Exception as e:
                logger.error(f"Ошибка при обработке номера телефона: {e}")
                await msg_event.reply("❌ Произошла ошибка при обработке номера.")

    async def prepare_message_sending(self, event, contact: Contact):
        """Подготовка к отправке сообщения конкретному контакту"""
        await event.reply(
            f"📝 Введите сообщение для отправки контакту:\n"
            f"👤 {contact.name}\n"
            f"📱 {contact.phone}"
        )

        @self.client.on(events.NewMessage(from_users=event.sender_id))
        async def message_handler(msg_event):
            try:
                # Отправляем сообщение
                message = await self.client.send_message(
                    contact.telegram_user_id or contact.phone,
                    msg_event.text
                )

                # Сохраняем сообщение в базу
                self.db.add_message(
                    contact_id=contact.id,
                    message_id=message.id,
                    direction='outgoing',
                    text=msg_event.text
                )

                await msg_event.reply(
                    "✅ Сообщение успешно отправлено!",
                    buttons=[[Button.inline("⬅️ Назад в меню", b"send_message")]]
                )

                # Удаляем временный обработчик
                self.client.remove_event_handler(message_handler)

            except Exception as e:
                logger.error(f"Ошибка при отправке сообщения: {e}")
                await msg_event.reply(
                    "❌ Ошибка при отправке сообщения.",
                    buttons=[[Button.inline("⬅️ Назад", b"send_message")]]
                )

    async def handle_message_history(self, event):
        """Обработка просмотра истории сообщений"""
        if not self.db.is_admin(event.sender_id):
            await event.answer("⛔ У вас нет прав администратора.", alert=True)
            return

        await event.edit(
            "🗂️ История переписки\n\n"
            "Выберите действие:",
            buttons=[
                [Button.inline("📇 Выбрать контакт", b"select_contact_for_history")],
                [Button.inline("📱 Ввести номер телефона", b"enter_phone_for_history")],
                [Button.inline("⬅️ Назад в главное меню", b"admin_menu")]
            ]
        )

    async def handle_incoming_message(self, event):
        """Обработка входящих сообщений"""
        try:
            # Получаем отправителя
            sender = await event.get_sender()
            
            # Ищем контакт в базе
            contact = self.db.get_contact_by_telegram_id(sender.id)
            if not contact:
                # Если контакт не найден, создаем новый
                phone = sender.phone if hasattr(sender, 'phone') else None
                contact_id = self.db.add_contact(
                    name=f"{sender.first_name or ''} {sender.last_name or ''}".strip(),
                    phone=phone or str(sender.id),
                    telegram_user_id=sender.id
                )
                contact = self.db.get_contact(contact_id)

            # Сохраняем сообщение в базу
            self.db.add_message(
                contact_id=contact.id,
                message_id=event.message.id,
                direction='incoming',
                text=event.message.text
            )

            # Уведомляем администраторов о новом сообщении
            admins = self.db.get_all_admins()
            for admin in admins:
                try:
                    await self.client.send_message(
                        admin.telegram_user_id,
                        f"📨 Новое сообщение от контакта:\n"
                        f"👤 {contact.name}\n"
                        f"📱 {contact.phone}\n\n"
                        f"💬 {event.message.text}"
                    )
                except Exception as e:
                    logger.error(f"Ошибка при уведомлении админа {admin.username}: {e}")

        except Exception as e:
            logger.error(f"Ошибка при обработке входящего сообщения: {e}") 