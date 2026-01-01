"""
WebSocket роутер для real-time синхронизации чек-листа.

Предоставляет WebSocket endpoint для получения обновлений в реальном времени.
"""

import logging

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.routing import APIRouter

from app.core.dependencies.cache import RedisDep
from app.core.websocket import ConnectionManager
from app.schemas.websocket import ConnectionEstablishedSchema, HeartbeatResponseSchema

logger = logging.getLogger(__name__)

# Глобальный экземпляр менеджера подключений
manager: ConnectionManager | None = None


def get_websocket_manager(redis: RedisDep) -> ConnectionManager:
    """
    Получает глобальный экземпляр ConnectionManager.

    Args:
        redis: Redis клиент

    Returns:
        ConnectionManager: Экземпляр менеджера подключений
    """
    global manager
    if manager is None:
        manager = ConnectionManager(redis=redis, channel="checklist:updates")
    return manager


class ChecklistWebSocketRouter:
    """
    WebSocket роутер для чек-листа.

    Предоставляет WebSocket endpoint для real-time обновлений.

    Endpoint:
        WS /checklist/ws - WebSocket соединение для обновлений

    Example client usage (JavaScript):
        ```javascript
        const ws = new WebSocket('ws://localhost:8001/api/v1/checklist/ws');

        ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            console.log('Received:', message);

            switch (message.type) {
                case 'task:updated':
                    updateTask(message.data);
                    break;
                case 'task:created':
                    addTask(message.data);
                    break;
                case 'task:deleted':
                    removeTask(message.data.id);
                    break;
            }
        };
        ```
    """

    def __init__(self):
        """Инициализирует ChecklistWebSocketRouter."""
        self.router = APIRouter(prefix="/checklist", tags=["Checklist - WebSocket"])
        self.configure()

    def configure(self):
        """Настройка WebSocket endpoint."""

        @self.router.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket, redis: RedisDep):
            """
            WebSocket endpoint для real-time синхронизации чек-листа.

            Клиенты подключаются к этому endpoint и получают обновления:
            - task:created - новая задача создана
            - task:updated - задача обновлена
            - task:deleted - задача удалена
            - category:updated - категория обновлена

            Args:
                websocket: WebSocket соединение
                redis: Redis клиент для PubSub
            """
            connection_manager = get_websocket_manager(redis)

            await connection_manager.connect(websocket)
            logger.info("Новое WebSocket подключение установлено")

            try:
                # Отправляем приветственное сообщение
                welcome_message = ConnectionEstablishedSchema(message="Подключено к чек-листу")
                await connection_manager.send_personal_message(welcome_message.model_dump(), websocket)

                # Ожидаем сообщения от клиента
                while True:
                    # Клиент может отправлять heartbeat для поддержания соединения
                    data = await websocket.receive_text()
                    logger.debug("Получено сообщение от клиента: %s", data)

                    # Обработка heartbeat
                    if data == "ping":
                        pong_message = HeartbeatResponseSchema()
                        await connection_manager.send_personal_message(pong_message.model_dump(), websocket)

            except WebSocketDisconnect:
                connection_manager.disconnect(websocket)
                logger.info("WebSocket подключение закрыто")
            except Exception as e:
                logger.error("Ошибка в WebSocket подключении: %s", e)
                connection_manager.disconnect(websocket)

    def get_router(self) -> APIRouter:
        """
        Возвращает настроенный APIRouter.

        Returns:
            APIRouter: Настроенный WebSocket роутер
        """
        return self.router
