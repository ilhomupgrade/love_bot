"""
Вспомогательные функции
"""

from datetime import datetime, timedelta


def generate_join_link(session_id: int, role: str) -> str:
    """
    Генерация ссылки для присоединения партнёра

    Args:
        session_id: ID сессии
        role: роль партнёра (partner1 или partner2)

    Returns:
        str: команда для присоединения
    """
    return f"/join_{session_id}_{role}"


def is_session_expired(created_at: datetime, max_hours: int = 24) -> bool:
    """
    Проверка, не истекла ли сессия

    Args:
        created_at: время создания сессии
        max_hours: максимальное время жизни сессии в часах

    Returns:
        bool: True если сессия истекла
    """
    expiry_time = created_at + timedelta(hours=max_hours)
    return datetime.now() > expiry_time
