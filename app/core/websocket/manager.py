"""
WebSocket Manager для real-time синхронизации.

Управляет WebSocket подключениями и использует Redis PubSub для
горизонтального масштабирования (синхронизация между несколькими серверами).
Поддерживает аутентификацию пользователей и отслеживание онлайн-статуса.
"""

import asyncio
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import WebSocket
from redis.asyncio import Redis

logger = logging.getLogger(__name__)


@dataclass
class OnlineUser:
    """Информация об онлайн-пользователе."""

    user_id: str
    username: str
    full_name: str | None
    role: str
    status: str = "online"  # online, away, idle
    connected_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    last_activity_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Преобразует в словарь для JSON."""
        return asdict(self)


@dataclass
class AuthenticatedConnection:
    """WebSocket соединение с информацией о пользователе."""

    websocket: WebSocket
    user: OnlineUser


class ConnectionManager:
    """
    Менеджер WebSocket подключений с поддержкой Redis PubSub.

    Управляет активными WebSocket подключениями и рассылает сообщения
    через Redis PubSub для поддержки горизонтального масштабирования.
    Отслеживает онлайн-статус аутентифицированных пользователей.

    Attributes:
        active_connections: Список активных WebSocket подключений (без аутентификации)
        authenticated_connections: Словарь аутентифицированных соединений {user_id: connection}
        redis: Redis клиент для PubSub
        pubsub: Redis PubSub объект
        channel_name: Название канала для рассылки сообщений

    Example:
        >>> manager = ConnectionManager(redis_client)
        >>> await manager.connect_authenticated(websocket, user_data)
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
        self.authenticated_connections: dict[str, AuthenticatedConnection] = {}
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
        logger.info(
            "WebSocket подключен. Активных соединений: %d", len(self.active_connections)
        )

        # Запускаем listener для Redis PubSub, если еще не запущен
        if self.redis and not self._listener_task:
            await self._start_pubsub_listener()

    async def connect_authenticated(
        self,
        websocket: WebSocket,
        user_id: str | UUID,
        username: str,
        full_name: str | None,
        role: str,
    ) -> OnlineUser:
        """
        Принимает аутентифицированное WebSocket подключение.

        Args:
            websocket: WebSocket соединение
            user_id: ID пользователя
            username: Имя пользователя
            full_name: Полное имя
            role: Роль пользователя

        Returns:
            OnlineUser: Информация об онлайн-пользователе

        Example:
            >>> user = await manager.connect_authenticated(
            ...     websocket, user.id, user.username, user.full_name, "admin"
            ... )
        """
        await websocket.accept()

        user_id_str = str(user_id)
        online_user = OnlineUser(
            user_id=user_id_str,
            username=username,
            full_name=full_name,
            role=role,
        )

        # Если пользователь уже подключен, отключаем старое соединение
        if user_id_str in self.authenticated_connections:
            old_conn = self.authenticated_connections[user_id_str]
            try:
                await old_conn.websocket.close(code=4000, reason="Новое подключение")
            except Exception:
                pass
            logger.info("Закрыто старое соединение для пользователя %s", username)

        self.authenticated_connections[user_id_str] = AuthenticatedConnection(
            websocket=websocket,
            user=online_user,
        )

        logger.info(
            "🟢 Пользователь %s онлайн. Всего онлайн: %d",
            username,
            len(self.authenticated_connections),
        )

        # Запускаем listener для Redis PubSub, если еще не запущен
        if self.redis and not self._listener_task:
            await self._start_pubsub_listener()

        # Уведомляем всех о новом пользователе онлайн
        await self.notify_user_online(online_user)

        return online_user

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
            logger.info(
                "WebSocket отключен. Активных соединений: %d",
                len(self.active_connections),
            )

        # Останавливаем listener если нет активных соединений
        if (
            not self.active_connections
            and not self.authenticated_connections
            and self._listener_task
        ):
            self._stop_pubsub_listener()

    async def disconnect_authenticated(self, user_id: str | UUID) -> OnlineUser | None:
        """
        Отключает аутентифицированного пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            OnlineUser | None: Информация об отключённом пользователе или None

        Example:
            >>> user = await manager.disconnect_authenticated(user_id)
        """
        user_id_str = str(user_id)

        if user_id_str not in self.authenticated_connections:
            return None

        connection = self.authenticated_connections.pop(user_id_str)
        online_user = connection.user

        logger.info(
            "🔴 Пользователь %s оффлайн. Всего онлайн: %d",
            online_user.username,
            len(self.authenticated_connections),
        )

        # Уведомляем всех о том, что пользователь ушёл
        await self.notify_user_offline(online_user)

        # Останавливаем listener если нет активных соединений
        if (
            not self.active_connections
            and not self.authenticated_connections
            and self._listener_task
        ):
            self._stop_pubsub_listener()

        return online_user

    def get_online_users(self) -> list[dict[str, Any]]:
        """
        Возвращает список онлайн-пользователей.

        Returns:
            list[dict]: Список словарей с информацией о пользователях

        Example:
            >>> users = manager.get_online_users()
            >>> # [{"user_id": "...", "username": "admin", ...}, ...]
        """
        return [conn.user.to_dict() for conn in self.authenticated_connections.values()]

    def get_online_count(self) -> int:
        """
        Возвращает количество онлайн-пользователей.

        Returns:
            int: Количество онлайн-пользователей
        """
        return len(self.authenticated_connections)

    def is_user_online(self, user_id: str | UUID) -> bool:
        """
        Проверяет, онлайн ли пользователь.

        Args:
            user_id: ID пользователя

        Returns:
            bool: True если онлайн
        """
        return str(user_id) in self.authenticated_connections

    async def send_personal_message(
        self, message: dict[str, Any], websocket: WebSocket
    ) -> None:
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

    async def send_to_user(self, user_id: str | UUID, message: dict[str, Any]) -> bool:
        """
        Отправляет сообщение конкретному пользователю.

        Args:
            user_id: ID пользователя
            message: Словарь с данными для отправки

        Returns:
            bool: True если сообщение отправлено

        Example:
            >>> await manager.send_to_user(user_id, {"type": "notification", ...})
        """
        user_id_str = str(user_id)
        if user_id_str not in self.authenticated_connections:
            return False

        connection = self.authenticated_connections[user_id_str]
        try:
            await connection.websocket.send_json(message)
            return True
        except Exception as e:
            logger.error("Ошибка отправки сообщения пользователю %s: %s", user_id_str, e)
            await self.disconnect_authenticated(user_id_str)
            return False

    async def broadcast(
        self, message: dict[str, Any], exclude: WebSocket | None = None
    ) -> None:
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

    async def _broadcast_local(
        self, message: dict[str, Any], exclude: WebSocket | None = None
    ) -> None:
        """
        Рассылает сообщение локальным WebSocket соединениям.

        Args:
            message: Словарь с данными для рассылки
            exclude: WebSocket соединение для исключения
        """
        disconnected = []

        # Рассылка неаутентифицированным соединениям
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

        # Рассылка аутентифицированным соединениям
        disconnected_users = []
        for user_id, auth_conn in self.authenticated_connections.items():
            if auth_conn.websocket == exclude:
                continue

            try:
                await auth_conn.websocket.send_json(message)
            except Exception as e:
                logger.error(
                    "Ошибка отправки сообщения пользователю %s: %s",
                    auth_conn.user.username,
                    e,
                )
                disconnected_users.append(user_id)

        # Удаляем отключенных пользователей
        for user_id in disconnected_users:
            await self.disconnect_authenticated(user_id)

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
            logger.info(
                "Запущен Redis PubSub listener для канала: %s", self.channel_name
            )
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
        При разрыве соединения автоматически переподключается.
        """
        retry_delay = 1.0
        max_retry_delay = 60.0

        while True:
            try:
                async for message in self.pubsub.listen():
                    if message["type"] == "message":
                        try:
                            data = json.loads(message["data"])
                            await self._broadcast_local(data)
                            logger.debug(
                                "Получено сообщение из Redis: %s", data.get("type")
                            )
                        except json.JSONDecodeError as e:
                            logger.error("Ошибка декодирования JSON из Redis: %s", e)
                    # Сбрасываем задержку при успешном получении сообщения
                    retry_delay = 1.0
            except asyncio.CancelledError:
                logger.info("Redis PubSub listener остановлен")
                await self.pubsub.unsubscribe(self.channel_name)
                await self.pubsub.close()
                break
            except Exception as e:
                logger.error(
                    "Ошибка в Redis PubSub listener: %s, переподключение через %s сек",
                    e,
                    retry_delay,
                )
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, max_retry_delay)

                # Переподключаемся к Redis PubSub
                try:
                    await self.pubsub.close()
                    self.pubsub = self.redis.pubsub()
                    await self.pubsub.subscribe(self.channel_name)
                    logger.info("✨ Переподключились к Redis PubSub")
                except Exception as reconnect_error:
                    logger.error(
                        "Ошибка переподключения к Redis PubSub: %s", reconnect_error
                    )

    # ===== Уведомления о пользователях =====

    async def notify_user_online(self, user: OnlineUser) -> None:
        """
        Уведомляет всех клиентов о том, что пользователь онлайн.

        Args:
            user: Информация об онлайн-пользователе

        Example:
            >>> await manager.notify_user_online(online_user)
        """
        message = {
            "type": "user:online",
            "data": user.to_dict(),
        }
        await self.broadcast(message)

    async def notify_user_offline(self, user: OnlineUser) -> None:
        """
        Уведомляет всех клиентов о том, что пользователь оффлайн.

        Args:
            user: Информация об оффлайн-пользователе

        Example:
            >>> await manager.notify_user_offline(online_user)
        """
        message = {
            "type": "user:offline",
            "data": user.to_dict(),
        }
        await self.broadcast(message)

    async def notify_user_updated(self, user_id: str, user_data: dict[str, Any]) -> None:
        """
        Уведомляет всех клиентов об обновлении данных пользователя.

        Также обновляет данные в authenticated_connections.

        Args:
            user_id: UUID пользователя
            user_data: Обновлённые данные (username, full_name, role)

        Example:
            >>> await manager.notify_user_updated(
            ...     str(user_id),
            ...     {"username": "new_name", "full_name": "Новое ФИО"}
            ... )
        """
        user_id_str = str(user_id)

        # Обновляем данные в authenticated_connections если пользователь онлайн
        if user_id_str in self.authenticated_connections:
            conn = self.authenticated_connections[user_id_str]
            old_user = conn.user
            # Создаём новый OnlineUser с обновлёнными данными
            updated_user = OnlineUser(
                user_id=old_user.user_id,
                username=user_data.get("username", old_user.username),
                full_name=user_data.get("full_name", old_user.full_name),
                role=user_data.get("role", old_user.role),
                connected_at=old_user.connected_at,
            )
            self.authenticated_connections[user_id_str] = AuthenticatedConnection(
                websocket=conn.websocket,
                user=updated_user,
            )

            # Отправляем уведомление всем клиентам
            message = {
                "type": "user:updated",
                "data": updated_user.to_dict(),
            }
            await self.broadcast(message)

            logger.info(
                "📝 Обновлены данные пользователя %s в списке онлайн",
                updated_user.username,
            )

    # ===== Уведомления о задачах =====

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

    async def notify_category_updated(
        self, category_id: UUID, category_data: dict[str, Any]
    ) -> None:
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

    # ===== Отслеживание активности =====

    async def update_user_activity(
        self, user_id: str, status: str = "online"
    ) -> bool:
        """
        Обновляет статус активности пользователя.

        Args:
            user_id: UUID пользователя
            status: Новый статус (online, away, idle)

        Returns:
            bool: True если статус обновлён

        Example:
            >>> await manager.update_user_activity(user_id, "away")
        """
        user_id_str = str(user_id)

        if user_id_str not in self.authenticated_connections:
            return False

        conn = self.authenticated_connections[user_id_str]
        old_user = conn.user
        now = datetime.now(UTC).isoformat()

        # Обновляем только если статус изменился или прошло время
        if old_user.status != status or old_user.last_activity_at != now:
            updated_user = OnlineUser(
                user_id=old_user.user_id,
                username=old_user.username,
                full_name=old_user.full_name,
                role=old_user.role,
                status=status,
                connected_at=old_user.connected_at,
                last_activity_at=now,
            )
            self.authenticated_connections[user_id_str] = AuthenticatedConnection(
                websocket=conn.websocket,
                user=updated_user,
            )

            # Уведомляем всех об изменении статуса
            if old_user.status != status:
                message = {
                    "type": "user:status",
                    "data": updated_user.to_dict(),
                }
                await self.broadcast(message)
                logger.debug(
                    "🔄 Статус пользователя %s изменён: %s -> %s",
                    old_user.username,
                    old_user.status,
                    status,
                )

            return True

        return False
