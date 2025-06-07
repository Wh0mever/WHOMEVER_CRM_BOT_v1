from telethon import types
from telethon.tl.functions.contacts import ImportContactsRequest
from loguru import logger
import Config
import asyncio

class TelegramContactsManager:
    """Менеджер для работы с контактами Telegram"""
    
    def __init__(self, client):
        self.client = client
    
    async def add_contact_to_telegram(self, name: str, phone: str) -> dict:
        """
        Добавляет контакт в Telegram
        
        Args:
            name: Имя контакта
            phone: Номер телефона контакта
            
        Returns:
            dict: Информация о результате добавления
        """
        
        try:
            # Добавляем задержку для соблюдения лимитов
            await asyncio.sleep(Config.MESSAGE_SEND_DELAY)
            
            # Создаем объект контакта
            input_contact = types.InputPhoneContact(
                client_id=0,  # Временный ID
                phone=phone,
                first_name=name.split()[0] if name else "Контакт",
                last_name=" ".join(name.split()[1:]) if len(name.split()) > 1 else ""
            )
            
            # Импортируем контакт
            result = await self.client(ImportContactsRequest([input_contact]))
            
            if result.imported:
                # Контакт успешно добавлен
                imported_contact = result.imported[0]
                user_id = imported_contact.user_id
                
                # Получаем информацию о пользователе
                try:
                    user = await self.client.get_entity(user_id)
                    logger.info(f"📱 Контакт добавлен в Telegram: {name} (@{user.username if user.username else user_id})")
                    
                    return {
                        "success": True,
                        "user_id": user_id,
                        "username": user.username,
                        "message": f"Контакт успешно добавлен в Telegram"
                    }
                except Exception as e:
                    logger.warning(f"Не удалось получить информацию о пользователе {user_id}: {e}")
                    return {
                        "success": True,
                        "user_id": user_id,
                        "username": None,
                        "message": f"Контакт добавлен, но не удалось получить дополнительную информацию"
                    }
            else:
                # Контакт не был импортирован (возможно, номер не зарегистрирован в Telegram)
                logger.warning(f"📱 Контакт не найден в Telegram: {phone}")
                return {
                    "success": False,
                    "user_id": None,
                    "username": None,
                    "message": "Номер телефона не зарегистрирован в Telegram"
                }
                
        except Exception as e:
            logger.error(f"❌ Ошибка при добавлении контакта в Telegram: {e}")
            return {
                "success": False,
                "user_id": None,
                "username": None,
                "message": f"Ошибка при добавлении: {str(e)}"
            }
    
    async def search_contact_in_telegram(self, phone: str) -> dict:
        """
        Ищет контакт в Telegram по номеру телефона
        
        Args:
            phone: Номер телефона
            
        Returns:
            dict: Информация о найденном контакте
        """
        
        try:
            # Пытаемся найти пользователя по номеру телефона
            user = await self.client.get_entity(phone)
            
            if user:
                logger.info(f"🔍 Контакт найден в Telegram: {phone} -> @{user.username if user.username else user.id}")
                return {
                    "found": True,
                    "user_id": user.id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "message": "Контакт найден в Telegram"
                }
            else:
                return {
                    "found": False,
                    "user_id": None,
                    "username": None,
                    "first_name": None,
                    "last_name": None,
                    "message": "Контакт не найден"
                }
                
        except Exception as e:
            logger.debug(f"Контакт {phone} не найден в Telegram: {e}")
            return {
                "found": False,
                "user_id": None,
                "username": None,
                "first_name": None,
                "last_name": None,
                "message": f"Контакт не найден: {str(e)}"
            }
    
    async def update_contact_info(self, contact_id: int, db) -> bool:
        """
        Обновляет информацию о контакте из Telegram
        
        Args:
            contact_id: ID контакта в базе данных
            db: Объект базы данных
            
        Returns:
            bool: Успешность обновления
        """
        
        try:
            # Получаем контакт из базы
            contact = db.get_contact(contact_id)
            if not contact:
                return False
            
            # Ищем контакт в Telegram
            telegram_info = await self.search_contact_in_telegram(contact.phone)
            
            if telegram_info["found"]:
                # Обновляем информацию в базе
                db.update_contact_telegram_id(contact_id, telegram_info["user_id"])
                logger.info(f"🔄 Обновлена информация о контакте: {contact.name} -> {telegram_info['user_id']}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Ошибка при обновлении информации о контакте {contact_id}: {e}")
            return False
    
    async def batch_import_contacts(self, contacts_list: list) -> dict:
        """
        Массовый импорт контактов в Telegram
        
        Args:
            contacts_list: Список контактов [(name, phone), ...]
            
        Returns:
            dict: Статистика импорта
        """
        
        if not contacts_list:
            return {"imported": 0, "failed": 0, "total": 0}
        
        try:
            # Создаем список контактов для импорта
            input_contacts = []
            for i, (name, phone) in enumerate(contacts_list):
                if len(input_contacts) >= Config.MAX_NEW_CONTACTS_PER_HOUR:
                    logger.warning(f"⚠️ Достигнут лимит импорта контактов: {Config.MAX_NEW_CONTACTS_PER_HOUR}")
                    break
                
                input_contact = types.InputPhoneContact(
                    client_id=i,
                    phone=phone,
                    first_name=name.split()[0] if name else "Контакт",
                    last_name=" ".join(name.split()[1:]) if len(name.split()) > 1 else ""
                )
                input_contacts.append(input_contact)
            
            # Импортируем контакты пакетом
            result = await self.client(ImportContactsRequest(input_contacts))
            
            imported_count = len(result.imported) if result.imported else 0
            total_count = len(input_contacts)
            failed_count = total_count - imported_count
            
            logger.info(f"📱 Массовый импорт завершен: {imported_count}/{total_count} успешно")
            
            return {
                "imported": imported_count,
                "failed": failed_count, 
                "total": total_count,
                "details": result
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка при массовом импорте контактов: {e}")
            return {
                "imported": 0,
                "failed": len(contacts_list),
                "total": len(contacts_list),
                "error": str(e)
            }
    
    async def delete_contact_from_telegram(self, user_id: int) -> bool:
        """
        Удаляет контакт из Telegram
        
        Args:
            user_id: ID пользователя в Telegram
            
        Returns:
            bool: Успешность удаления
        """
        
        try:
            # Удаляем контакт
            await self.client(types.contacts.DeleteContactsRequest([user_id]))
            logger.info(f"🗑️ Контакт удален из Telegram: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка при удалении контакта {user_id}: {e}")
            return False 