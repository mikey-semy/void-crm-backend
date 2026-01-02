"""
WebSocket роутер для пользователей с аутентификацией.

Предоставляет WebSocket endpoint с JWT аутентификацией
и отслеживанием онлайн-статуса пользователей.
"""

import logging
from uuid import UUID

from fastapi import Query, WebSocket, WebSocketDisconnect
from fastapi.routing import APIRouter

from app.core.dependencies.cache import RedisDep
from app.core.dependencies.websocket import get_websocket_manager
from app.core.security import TokenManager, TokenType
from app.repository.v1.users import UserRepository
from app.schemas.websocket import ConnectionEstablishedSchema, HeartbeatResponseSchema

logger = logging.getLogger(__name__)


class UsersWebSocketRouter:
    """
    WebSocket роутер для пользователей с аутентификацией.

    Предоставляет WebSocket endpoint с JWT аутентификацией,
    отслеживает онлайн-статус и рассылает уведомления.

    Endpoints:
        WS /users/ws - Аутентифицированное WebSocket соединение
        GET /users/online - Список онлайн-пользователей

    Example client usage (JavaScript):
        ```javascript
        const token = localStorage.getItem('access_token');
        const ws = new WebSocket(`ws://localhost:8001/api/v1/users/ws?token=${token}`);

        ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            console.log('Received:', message);

            switch (message.type) {
                case 'user:online':
                    console.log('User came online:', message.data);
                    break;
                case 'user:offline':
                    console.log('User went offline:', message.data);
                    break;
            }
        };

        // Heartbeat
        setInterval(() => ws.send('ping'), 30000);
        ```
    """

    def __init__(self):
        """Инициализирует UsersWebSocketRouter."""
        self.router = APIRouter(prefix="/users", tags=["Users - WebSocket"])
        self.configure()

    def configure(self):
        """Настройка WebSocket и HTTP endpoints."""

        @self.router.websocket("/ws")
        async def websocket_endpoint(
            websocket: WebSocket,
            redis: RedisDep,
            token: str = Query(..., description="JWT access token"),
        ):
            """
            Аутентифицированный WebSocket endpoint.

            Клиенты подключаются с JWT токеном и получают:
            - user:online - пользователь подключился
            - user:offline - пользователь отключился
            - Все события чек-листа (task:*, category:*)

            Args:
                websocket: WebSocket соединение
                redis: Redis клиент для PubSub
                token: JWT access token (query parameter)
            """
            connection_manager = get_websocket_manager(redis)

            # Валидируем токен
            try:
                payload = TokenManager.decode_token(token)
                TokenManager.validate_token_payload(payload, TokenType.ACCESS)
                user_id = UUID(payload.get("sub"))
            except Exception as e:
                logger.warning("WebSocket: невалидный токен: %s", e)
                await websocket.close(code=4001, reason="Invalid token")
                return

            # Получаем данные пользователя из БД
            from app.core.dependencies.database import get_async_session

            session_gen = get_async_session()
            session = await anext(session_gen)

            try:
                user_repo = UserRepository(session=session)
                user = await user_repo.get_item_by_id(user_id)

                if not user:
                    await websocket.close(code=4004, reason="User not found")
                    return

                if not user.is_active:
                    await websocket.close(code=4003, reason="User is deactivated")
                    return

                # Получаем роль пользователя
                role = "user"
                if user.user_roles:
                    role = user.user_roles[0].role_code.value

                # Подключаем пользователя
                online_user = await connection_manager.connect_authenticated(
                    websocket=websocket,
                    user_id=user.id,
                    username=user.username,
                    full_name=user.full_name,
                    role=role,
                )

                logger.info(
                    "WebSocket: пользователь %s подключён", online_user.username
                )

                # Отправляем приветственное сообщение со списком онлайн-пользователей
                online_users_list = connection_manager.get_online_users()
                logger.info(
                    "WebSocket: отправляем список онлайн-пользователей (%d): %s",
                    len(online_users_list),
                    [u.get("username") for u in online_users_list],
                )
                welcome_message = ConnectionEstablishedSchema(
                    message="Подключено к CRM",
                    data={
                        "user": online_user.to_dict(),
                        "online_users": online_users_list,
                        "online_count": connection_manager.get_online_count(),
                    },
                )
                await connection_manager.send_personal_message(
                    welcome_message.model_dump(), websocket
                )

                # Ожидаем сообщения от клиента
                while True:
                    data = await websocket.receive_text()
                    logger.debug(
                        "WebSocket: сообщение от %s: %s", online_user.username, data
                    )

                    # Обработка heartbeat
                    if data == "ping":
                        pong_message = HeartbeatResponseSchema()
                        await connection_manager.send_personal_message(
                            pong_message.model_dump(), websocket
                        )
                    # Обработка активности - пользователь активен
                    elif data == "activity":
                        await connection_manager.update_user_activity(
                            str(user_id), "online"
                        )
                    # Обработка статуса "отошёл"
                    elif data == "away":
                        await connection_manager.update_user_activity(
                            str(user_id), "away"
                        )
                    # Обработка статуса "неактивен"
                    elif data == "idle":
                        await connection_manager.update_user_activity(
                            str(user_id), "idle"
                        )

            except WebSocketDisconnect:
                await connection_manager.disconnect_authenticated(user_id)
                logger.info("WebSocket: пользователь отключился")
            except Exception as e:
                logger.error("WebSocket: ошибка: %s", e)
                await connection_manager.disconnect_authenticated(user_id)
            finally:
                await session.close()

        @self.router.get("/online")
        async def get_online_users(redis: RedisDep):
            """
            Возвращает список онлайн-пользователей.

            Returns:
                dict: Список онлайн-пользователей и их количество
            """
            connection_manager = get_websocket_manager(redis)

            return {
                "success": True,
                "data": {
                    "users": connection_manager.get_online_users(),
                    "count": connection_manager.get_online_count(),
                },
            }

    def get_router(self) -> APIRouter:
        """
        Возвращает настроенный APIRouter.

        Returns:
            APIRouter: Настроенный WebSocket роутер
        """
        return self.router
