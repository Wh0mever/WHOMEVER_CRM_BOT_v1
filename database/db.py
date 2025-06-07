import sqlite3
from loguru import logger
from typing import List, Optional
from .models import Contact, Message, Admin
from .models import CREATE_CONTACTS_TABLE, CREATE_MESSAGES_TABLE, CREATE_ADMINS_TABLE

class Database:
    def __init__(self, db_path: str = "telegram_crm.db"):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        """Инициализация базы данных и создание таблиц"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Создаем таблицы
            cursor.execute(CREATE_CONTACTS_TABLE)
            cursor.execute(CREATE_MESSAGES_TABLE)
            cursor.execute(CREATE_ADMINS_TABLE)
            
            conn.commit()
            logger.info("База данных успешно инициализирована")
        except Exception as e:
            logger.error(f"Ошибка при инициализации базы данных: {e}")
        finally:
            conn.close()

    # Методы для работы с контактами
    def add_contact(self, name: str, phone: str, note: str = None, telegram_user_id: int = None) -> int:
        """Добавление нового контакта"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO contacts (name, phone, note, telegram_user_id) VALUES (?, ?, ?, ?)",
                (name, phone, note, telegram_user_id)
            )
            conn.commit()
            contact_id = cursor.lastrowid
            logger.info(f"➕ Контакт добавлен в базу: {name} ({phone}) [ID: {contact_id}]")
            return contact_id
        finally:
            conn.close()

    def get_contact(self, contact_id: int) -> Optional[Contact]:
        """Получение контакта по ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,))
            result = cursor.fetchone()
            if result:
                # Конвертируем строку даты в datetime объект
                contact = Contact(*result)
                if isinstance(contact.date_added, str):
                    from datetime import datetime
                    contact.date_added = datetime.strptime(contact.date_added, '%Y-%m-%d %H:%M:%S')
                return contact
            return None
        finally:
            conn.close()

    def get_contact_by_phone(self, phone: str) -> Optional[Contact]:
        """Получение контакта по номеру телефона"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM contacts WHERE phone = ?", (phone,))
            result = cursor.fetchone()
            if result:
                contact = Contact(*result)
                if isinstance(contact.date_added, str):
                    from datetime import datetime
                    contact.date_added = datetime.strptime(contact.date_added, '%Y-%m-%d %H:%M:%S')
                return contact
            return None
        finally:
            conn.close()

    def get_contact_by_telegram_id(self, telegram_user_id: int) -> Optional[Contact]:
        """Получение контакта по Telegram ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM contacts WHERE telegram_user_id = ?", (telegram_user_id,))
            result = cursor.fetchone()
            if result:
                contact = Contact(*result)
                if isinstance(contact.date_added, str):
                    from datetime import datetime
                    contact.date_added = datetime.strptime(contact.date_added, '%Y-%m-%d %H:%M:%S')
                return contact
            return None
        finally:
            conn.close()

    def get_recent_contacts(self, limit: int = 10) -> List[Contact]:
        """Получение последних контактов"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM contacts ORDER BY date_added DESC LIMIT ?", (limit,))
            return [Contact(*row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_all_contacts(self, limit: int = 50, offset: int = 0) -> List[Contact]:
        """Получение всех контактов с пагинацией"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM contacts ORDER BY name LIMIT ? OFFSET ?", (limit, offset))
            return [Contact(*row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def update_contact(self, contact_id: int, name: str = None, phone: str = None, note: str = None):
        """Обновление контакта"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            updates = []
            params = []
            
            if name is not None:
                updates.append("name = ?")
                params.append(name)
            if phone is not None:
                updates.append("phone = ?")
                params.append(phone)
            if note is not None:
                updates.append("note = ?")
                params.append(note)
            
            if updates:
                params.append(contact_id)
                cursor.execute(f"UPDATE contacts SET {', '.join(updates)} WHERE id = ?", params)
                conn.commit()
        finally:
            conn.close()

    def update_contact_telegram_id(self, contact_id: int, telegram_user_id: int):
        """Обновление Telegram ID контакта"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE contacts SET telegram_user_id = ? WHERE id = ?", 
                         (telegram_user_id, contact_id))
            conn.commit()
        finally:
            conn.close()

    def delete_contact(self, contact_id: int):
        """Удаление контакта"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
            conn.commit()
        finally:
            conn.close()

    def search_contacts(self, query: str) -> List[Contact]:
        """Поиск контактов по имени, телефону или примечанию"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT * FROM contacts WHERE name LIKE ? OR phone LIKE ? OR note LIKE ?",
                (f"%{query}%", f"%{query}%", f"%{query}%")
            )
            contacts = []
            for row in cursor.fetchall():
                contact = Contact(*row)
                # Конвертируем строку даты в datetime объект
                if isinstance(contact.date_added, str):
                    from datetime import datetime
                    contact.date_added = datetime.strptime(contact.date_added, '%Y-%m-%d %H:%M:%S')
                contacts.append(contact)
            return contacts
        finally:
            conn.close()

    def get_contacts_count(self) -> int:
        """Получение общего количества контактов"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM contacts")
            return cursor.fetchone()[0]
        finally:
            conn.close()

    # Методы для работы с сообщениями
    def add_message(self, contact_id: int, message_id: int, direction: str,
                   text: str, media_type: str = 'text', media_file_id: str = None) -> int:
        """Добавление нового сообщения"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """INSERT INTO messages 
                   (contact_id, message_id, direction, text, media_type, media_file_id)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (contact_id, message_id, direction, text, media_type, media_file_id)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_contact_messages(self, contact_id: int, limit: int = 20) -> List[Message]:
        """Получение истории сообщений контакта"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT * FROM messages WHERE contact_id = ? ORDER BY timestamp DESC LIMIT ?",
                (contact_id, limit)
            )
            messages = []
            for row in cursor.fetchall():
                message = Message(*row)
                # Конвертируем строку даты в datetime объект
                if isinstance(message.timestamp, str):
                    from datetime import datetime
                    message.timestamp = datetime.strptime(message.timestamp, '%Y-%m-%d %H:%M:%S')
                messages.append(message)
            return messages
        finally:
            conn.close()

    def get_messages_count(self) -> int:
        """Получение общего количества сообщений"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM messages")
            return cursor.fetchone()[0]
        finally:
            conn.close()

    def get_messages_count_by_period(self, period_days: int = 1) -> int:
        """Получение количества сообщений за период"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT COUNT(*) FROM messages WHERE timestamp >= datetime('now', '-{} days')".format(period_days)
            )
            return cursor.fetchone()[0]
        finally:
            conn.close()

    def get_message_by_id(self, contact_id: int, message_id: int) -> Optional[Message]:
        """Получение сообщения по ID контакта и ID сообщения"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT * FROM messages WHERE contact_id = ? AND message_id = ?",
                (contact_id, message_id)
            )
            result = cursor.fetchone()
            if result:
                message = Message(*result)
                # Конвертируем строку даты в datetime объект
                if isinstance(message.timestamp, str):
                    from datetime import datetime
                    message.timestamp = datetime.strptime(message.timestamp, '%Y-%m-%d %H:%M:%S')
                return message
            return None
        finally:
            conn.close()

    # Методы для работы с администраторами
    def add_admin(self, username: str, telegram_user_id: int) -> int:
        """Добавление нового администратора"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO admins (username, telegram_user_id) VALUES (?, ?)",
                (username, telegram_user_id)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def remove_admin(self, telegram_user_id: int):
        """Удаление администратора"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM admins WHERE telegram_user_id = ?", (telegram_user_id,))
            conn.commit()
        finally:
            conn.close()

    def is_admin(self, telegram_user_id: int) -> bool:
        """Проверка, является ли пользователь администратором"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id FROM admins WHERE telegram_user_id = ?", (telegram_user_id,))
            return cursor.fetchone() is not None
        finally:
            conn.close()

    def get_all_admins(self) -> List[Admin]:
        """Получение списка всех администраторов"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM admins ORDER BY date_added")
            admins = []
            for row in cursor.fetchall():
                admin = Admin(*row)
                # Конвертируем строку даты в datetime объект
                if isinstance(admin.date_added, str):
                    from datetime import datetime
                    admin.date_added = datetime.strptime(admin.date_added, '%Y-%m-%d %H:%M:%S')
                admins.append(admin)
            return admins
        finally:
            conn.close()

    def get_admin_by_username(self, username: str) -> Optional[Admin]:
        """Получение админа по username"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM admins WHERE username = ?", (username,))
            result = cursor.fetchone()
            return Admin(*result) if result else None
        finally:
            conn.close()

    def remove_duplicate_admins(self):
        """Удаление дублированных администраторов"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # Удаляем дубликаты, оставляя только первую запись для каждого telegram_user_id
            cursor.execute("""
                DELETE FROM admins 
                WHERE id NOT IN (
                    SELECT MIN(id) 
                    FROM admins 
                    GROUP BY telegram_user_id
                )
            """)
            conn.commit()
            deleted_count = cursor.rowcount
            logger.info(f"🧹 Удалено дублированных админов: {deleted_count}")
            return deleted_count
        except Exception as e:
            logger.error(f"Ошибка при удалении дубликатов: {e}")
            return 0
        finally:
            conn.close() 