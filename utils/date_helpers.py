"""
Утилиты для работы с датами в CRM системе
"""

from datetime import datetime
from typing import Union


def parse_sqlite_datetime(date_string: Union[str, datetime]) -> datetime:
    """
    Конвертирует строку даты из SQLite в объект datetime
    
    Args:
        date_string: Строка даты или уже datetime объект
        
    Returns:
        datetime объект
    """
    if isinstance(date_string, datetime):
        return date_string
    
    if isinstance(date_string, str):
        try:
            # Формат SQLite: 'YYYY-MM-DD HH:MM:SS'
            return datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            try:
                # Альтернативный формат
                return datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S.%f')
            except ValueError:
                # Если не удается распарсить, возвращаем текущее время
                return datetime.now()
    
    return datetime.now()


def format_date_display(date_obj: Union[str, datetime], format_type: str = "full") -> str:
    """
    Форматирует дату для отображения пользователю
    
    Args:
        date_obj: Объект даты или строка
        format_type: Тип форматирования ('full', 'short', 'time_only')
        
    Returns:
        Отформатированная строка даты
    """
    if isinstance(date_obj, str):
        date_obj = parse_sqlite_datetime(date_obj)
    
    if not isinstance(date_obj, datetime):
        return "Неизвестно"
    
    formats = {
        "full": "%d.%m.%Y %H:%M",
        "short": "%d.%m.%Y", 
        "time_only": "%H:%M",
        "message": "%d.%m %H:%M"
    }
    
    return date_obj.strftime(formats.get(format_type, formats["full"]))


def get_relative_time(date_obj: Union[str, datetime]) -> str:
    """
    Возвращает относительное время (например, "2 часа назад")
    
    Args:
        date_obj: Объект даты или строка
        
    Returns:
        Строка с относительным временем
    """
    if isinstance(date_obj, str):
        date_obj = parse_sqlite_datetime(date_obj)
    
    if not isinstance(date_obj, datetime):
        return "Неизвестно"
    
    now = datetime.now()
    diff = now - date_obj
    
    if diff.days > 7:
        return format_date_display(date_obj, "short")
    elif diff.days > 0:
        return f"{diff.days} дн. назад"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} ч. назад"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} мин. назад"
    else:
        return "Только что"


def is_today(date_obj: Union[str, datetime]) -> bool:
    """
    Проверяет, является ли дата сегодняшней
    
    Args:
        date_obj: Объект даты или строка
        
    Returns:
        True если дата сегодняшняя
    """
    if isinstance(date_obj, str):
        date_obj = parse_sqlite_datetime(date_obj)
    
    if not isinstance(date_obj, datetime):
        return False
    
    return date_obj.date() == datetime.now().date()


def is_recent(date_obj: Union[str, datetime], hours: int = 24) -> bool:
    """
    Проверяет, была ли дата в последние N часов
    
    Args:
        date_obj: Объект даты или строка
        hours: Количество часов для проверки
        
    Returns:
        True если дата в указанном периоде
    """
    if isinstance(date_obj, str):
        date_obj = parse_sqlite_datetime(date_obj)
    
    if not isinstance(date_obj, datetime):
        return False
    
    now = datetime.now()
    diff = now - date_obj
    
    return diff.total_seconds() <= (hours * 3600) 