"""
Зависимости для WebSocket.

Предоставляет dependency injection для WebSocket Manager.
"""

from typing import Annotated

from fastapi import Depends

from app.core.dependencies.cache import RedisDep
from app.core.websocket import ConnectionManager

# Глобальный экземпляр менеджера подключений
_manager: ConnectionManager | None = None


def get_websocket_manager(redis: RedisDep) -> ConnectionManager:
    """
    Получает глобальный экземпляр ConnectionManager.

    Args:
        redis: Redis клиент

    Returns:
        ConnectionManager: Экземпляр менеджера подключений
    """
    global _manager
    if _manager is None:
        _manager = ConnectionManager(redis=redis, channel="checklist:updates")
    return _manager


# Type alias для dependency injection
WebSocketManagerDep = Annotated[ConnectionManager, Depends(get_websocket_manager)]
