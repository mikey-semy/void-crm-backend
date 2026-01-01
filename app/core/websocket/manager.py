"""
WebSocket Manager для real-time синхронизации чек-листа.

Управляет WebSocket подключениями и использует Redis PubSub для
горизонтального масштабирования (синхронизация между несколькими серверами).
"""

import asyncio
import json
import logging
from typing import Any
from uuid import UUID

from fastapi import WebSocket
from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Менеджер WebSocket подключений с поддержкой Redis PubSub.

    Управляет активными WebSocket подключениями и рассылает сообщения
    через Redis PubSub для поддержки горизонтального масштабирования.

    Attributes:
        active_connections: Список активных WebSocket подключений
        redis: Redis клиент для PubSub
        pubsub: Redis PubSub объект
        channel_name: Название канала для рассылки сообщений

    Example:
        >>> manager = ConnectionManager(redis_client)
        >>> await manager.connect(websocket)
        >>> await manager.broadcast({"type": "task:updated", "data": {...}})
    """

    def __init__(self, redis: Redis | None = None, channel: str = "checklist:updates"):
        """
        Инициализирует ConnectionManager.

        Args:
            redis: Redis клиент для PubSub (опционально)
            channel: Название канала для рассылки сообщений
        """
        self.active_connections: list[WebSocket] = []
        self.redis = redis
        self.pubsub = None
        self.channel_name = channel
        self._listener_task: asyncio.Task | None = None

    async def connect(self, websocket: WebSocket) -> None:
        """
        Принимает WebSocket подключение и добавляет в список активных.

        Args:
            websocket: WebSocket соединение

        Example:
            >>> await manager.connect(websocket)
        """
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("WebSocket подключен. Активных соединений: %d", len(self.active_connections))

        # Запускаем listener для Redis PubSub, если еще не запущен
        if self.redis and not self._listener_task:
            await self._start_pubsub_listener()

    def disconnect(self, websocket: WebSocket) -> None:
        """
        Удаляет WebSocket из списка активных соединений.

        Args:
            websocket: WebSocket соединение для отключения

        Example:
            >>> manager.disconnect(websocket)
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("WebSocket отключен. Активных соединений: %d", len(self.active_connections))

        # Останавливаем listener если нет активных соединений
        if not self.active_connections and self._listener_task:
            self._stop_pubsub_listener()

    async def send_personal_message(self, message: dict[str, Any], websocket: WebSocket) -> None:
        """
        Отправляет сообщение конкретному WebSocket соединению.

        Args:
            message: Словарь с данными для отправки
            websocket: Целевое WebSocket соединение

        Example:
            >>> await manager.send_personal_message(
            ...     {"type": "connection:established"},
            ...     websocket
            ... )
        """
        try:
            await websocket.send_json(message)
            logger.debug("Отправлено персональное сообщение: %s", message.get("type"))
        except Exception as e:
            logger.error("Ошибка отправки персонального сообщения: %s", e)
            self.disconnect(websocket)

    async def broadcast(self, message: dict[str, Any], exclude: WebSocket | None = None) -> None:
        """
        Рассылает сообщение всем активным WebSocket соединениям.

        Если используется Redis, публикует сообщение в PubSub канал
        для синхронизации с другими серверами.

        Args:
            message: Словарь с данными для рассылки
            exclude: WebSocket соединение, которое нужно исключить из рассылки

        Example:
            >>> await manager.broadcast({
            ...     "type": "task:updated",
            ...     "data": {"id": "...", "status": "completed"}
            ... })
        """
        # Рассылка локальным соединениям
        await self._broadcast_local(message, exclude)

        # Публикация в Redis PubSub для других серверов
        if self.redis:
            await self._publish_to_redis(message)

    async def _broadcast_local(self, message: dict[str, Any], exclude: WebSocket | None = None) -> None:
        """
        Рассылает сообщение локальным WebSocket соединениям.

        Args:
            message: Словарь с данными для рассылки
            exclude: WebSocket соединение для исключения
        """
        disconnected = []

        for connection in self.active_connections:
            if connection == exclude:
                continue

            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error("Ошибка отправки сообщения: %s", e)
                disconnected.append(connection)

        # Удаляем отключенные соединения
        for conn in disconnected:
            self.disconnect(conn)

        if disconnected:
            logger.info("Отключено %d соединений при рассылке", len(disconnected))

    async def _publish_to_redis(self, message: dict[str, Any]) -> None:
        """
        Публикует сообщение в Redis PubSub канал.

        Args:
            message: Словарь с данными для публикации
        """
        try:
            message_json = json.dumps(message, default=str)
            await self.redis.publish(self.channel_name, message_json)
            logger.debug("Опубликовано в Redis: %s", message.get("type"))
        except Exception as e:
            logger.error("Ошибка публикации в Redis: %s", e)

    async def _start_pubsub_listener(self) -> None:
        """
        Запускает фоновую задачу для прослушивания Redis PubSub канала.

        Получает сообщения из Redis и рассылает их локальным соединениям.
        """
        try:
            self.pubsub = self.redis.pubsub()
            await self.pubsub.subscribe(self.channel_name)
            self._listener_task = asyncio.create_task(self._listen_redis())
            logger.info("Запущен Redis PubSub listener для канала: %s", self.channel_name)
        except Exception as e:
            logger.error("Ошибка запуска Redis PubSub listener: %s", e)

    def _stop_pubsub_listener(self) -> None:
        """
        Останавливает фоновую задачу прослушивания Redis PubSub.
        """
        if self._listener_task:
            self._listener_task.cancel()
            self._listener_task = None
            logger.info("Остановлен Redis PubSub listener")

    async def _listen_redis(self) -> None:
        """
        Фоновая задача для прослушивания сообщений из Redis PubSub.

        Получает сообщения и рассылает их всем локальным WebSocket соединениям.
        """
        try:
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        await self._broadcast_local(data)
                        logger.debug("Получено сообщение из Redis: %s", data.get("type"))
                    except json.JSONDecodeError as e:
                        logger.error("Ошибка декодирования JSON из Redis: %s", e)
        except asyncio.CancelledError:
            logger.info("Redis PubSub listener остановлен")
            await self.pubsub.unsubscribe(self.channel_name)
            await self.pubsub.close()
        except Exception as e:
            logger.error("Ошибка в Redis PubSub listener: %s", e)

    async def notify_task_updated(self, task_id: UUID, task_data: dict[str, Any]) -> None:
        """
        Уведомляет всех клиентов об обновлении задачи.

        Args:
            task_id: UUID обновленной задачи
            task_data: Данные обновленной задачи

        Example:
            >>> await manager.notify_task_updated(
            ...     task_id,
            ...     {"id": str(task_id), "status": "completed", ...}
            ... )
        """
        message = {"type": "task:updated", "data": {"id": str(task_id), **task_data}}
        await self.broadcast(message)

    async def notify_category_updated(self, category_id: UUID, category_data: dict[str, Any]) -> None:
        """
        Уведомляет всех клиентов об обновлении категории.

        Args:
            category_id: UUID обновленной категории
            category_data: Данные обновленной категории

        Example:
            >>> await manager.notify_category_updated(
            ...     category_id,
            ...     {"id": str(category_id), "title": "Новое название", ...}
            ... )
        """
        message = {
            "type": "category:updated",
            "data": {"id": str(category_id), **category_data},
        }
        await self.broadcast(message)

    async def notify_task_created(self, task_data: dict[str, Any]) -> None:
        """
        Уведомляет всех клиентов о создании новой задачи.

        Args:
            task_data: Данные созданной задачи

        Example:
            >>> await manager.notify_task_created(
            ...     {"id": str(task_id), "title": "Новая задача", ...}
            ... )
        """
        message = {"type": "task:created", "data": task_data}
        await self.broadcast(message)

    async def notify_task_deleted(self, task_id: UUID) -> None:
        """
        Уведомляет всех клиентов об удалении задачи.

        Args:
            task_id: UUID удаленной задачи

        Example:
            >>> await manager.notify_task_deleted(task_id)
        """
        message = {"type": "task:deleted", "data": {"id": str(task_id)}}
        await self.broadcast(message)
