"""
Redis менеджер для аутентификации.

Управляет хранением и валидацией токенов, сессий пользователей,
статусов онлайн и последней активности через Redis.
"""

import json
import logging
import uuid
from datetime import UTC, datetime
from uuid import UUID

from redis.asyncio import Redis

from app.core.exceptions import ForbiddenError, TokenInvalidError
from app.core.integrations.cache.base import BaseRedisManager
from app.core.security import TokenManager
from app.core.settings import settings
from app.schemas.v1.auth.base import UserCredentialsSchema, UserSchema

logger = logging.getLogger(__name__)


class AuthRedisManager(BaseRedisManager):
    """
    Redis менеджер для аутентификации.

    Предоставляет методы для работы с токенами, сессиями и статусами пользователей.
    """

    def __init__(self, redis: Redis):
        super().__init__(redis)

    async def save_token(self, user: UserCredentialsSchema, token: str) -> None:
        """
        Сохраняет токен пользователя в Redis.

        Args:
            user: Данные пользователя.
            token: Токен пользователя.

        Returns:
            None
        """
        user_data = self._prepare_user_data(user)

        await self.set(
            key=f"token:{token}",
            value=json.dumps(user_data),
            expires=settings.ACCESS_TOKEN_MAX_AGE,
        )
        await self.sadd(f"sessions:{user.email}", token)

        # Добавляем установку online статуса при входе
        await self.set_online_status(user.id, True)
        await self.update_last_activity(token)

    async def get_user_by_token(self, token: str) -> UserSchema | None:
        """
        Получает пользователя по токену.

        Args:
            token: Токен пользователя.

        Returns:
            Данные пользователя или None, если пользователь не найден.
        """
        user_data = await self.get(f"token:{token}")
        return UserSchema.model_validate_json(user_data) if user_data else None

    async def remove_token(self, token: str) -> None:
        """
        Удаляет токен пользователя из Redis.

        Args:
            token: Токен пользователя.

        Returns:
            None
        """
        user_data = await self.get(f"token:{token}")
        if user_data:
            user = UserSchema.model_validate_json(user_data)
            await self.srem(f"sessions:{user.email}", token)
        await self.delete(f"token:{token}")

    @staticmethod
    def _prepare_user_data(user: UserCredentialsSchema) -> dict:
        """
        Подготовка данных пользователя для сохранения

        Конвертируем datetime в строки для отправки в Redis,
        иначе TypeError: Object of type datetime is not JSON serializable

        Args:
            user: Данные пользователя.

        Returns:
            Данные пользователя для сохранения.
        """
        user_data = user.model_dump()
        for key, value in user_data.items():
            if isinstance(value, datetime):
                user_data[key] = value.isoformat()

        if "id" in user_data and isinstance(user_data["id"], UUID):
            user_data["id"] = str(user_data["id"])

        return user_data

    async def get_user_from_redis(
        self, token: str, email: str
    ) -> UserCredentialsSchema:
        """
        Получает пользователя из Redis или создает базовый объект

        Args:
            token: Токен пользователя.
            email: Email пользователя.

        Returns:
            Данные пользователя.
        """
        stored_token = await self.get(f"token:{token}")

        if stored_token:
            user_data = json.loads(stored_token)
            return UserCredentialsSchema.model_validate(user_data)

        return UserCredentialsSchema(
            id=uuid.uuid4(),
            email=email,
            password_hash="",
            is_active=True,
            full_name="",
            role="buyer",
        )

    async def verify_and_get_user(self, token: str) -> UserCredentialsSchema:
        """
        Основной метод проверки токена и получения пользователя

        Args:
            token: Токен пользователя.

        Returns:
            Данные пользователя.
        """
        logger.debug("Начало верификации токена: %s", token)

        if not token:
            logger.debug("Токен отсутствует")
            raise TokenInvalidError()
        try:
            payload = TokenManager.decode_token(token)
            logger.debug("Получен payload: %s", payload)

            email = TokenManager.validate_payload(payload)
            logger.debug("Получен email: %s", email)

            user = await self.get_user_from_redis(token, email)
            logger.debug("Получен пользователь: %s", user)
            logger.debug("Проверка активации пользователя: %s", user.is_active)

            if not user.is_active:
                raise ForbiddenError(
                    detail="Аккаунт деактивирован", extra={"user_id": user.id}
                )

            return user

        except Exception as e:
            logger.debug("Ошибка при верификации: %s", str(e))
            raise

    async def get_all_tokens(self) -> list[str]:
        """
        Получает все активные токены из Redis

        Returns:
            list[str]: Список активных токенов
        """
        # Получаем все ключи по паттерну token:*
        keys = await self.keys("token:*")

        # Убираем префикс token: из ключей
        tokens = [key.decode().split(":")[-1] for key in keys]

        return tokens

    async def update_last_activity(self, token: str) -> None:
        """
        Обновляет время последней активности пользователя

        Args:
            token: Токен пользователя

        Returns:
            None
        """
        await self.set(
            f"last_activity:{token}", str(int(datetime.now(UTC).timestamp()))
        )

    async def get_last_activity(self, token: str) -> int | None:
        """
        Получает время последней активности пользователя

        Args:
            token: Токен пользователя

        Returns:
            int: Время последней активности пользователя в формате timestamp (секунды)
        """
        timestamp = await self.get(f"last_activity:{token}")
        return int(timestamp) if timestamp else 0

    async def set_online_status(self, user_id: uuid.UUID, is_online: bool) -> None:
        """
        Устанавливает статус онлайн/офлайн пользователя

        Args:
            user_id: ID пользователя
            is_online: Статус онлайн/офлайн

        Returns:
            None
        """
        await self.set(
            key=f"online:{user_id}",
            value=str(is_online),
            expires=settings.ACCESS_TOKEN_MAX_AGE if is_online else None,
        )

    async def get_online_status(self, user_id: uuid.UUID) -> bool:
        """
        Получает статус онлайн/офлайн пользователя

        Args:
            user_id: ID пользователя

        Returns:
            bool: Статус онлайн/офлайн пользователя
        """
        status = await self.get(f"online:{user_id}")

        if status is None:
            return False

        if isinstance(status, bytes):
            return status.decode("utf-8") == "True"
        else:
            return status == "True"

    async def get_user_sessions(self, email: str) -> list[str]:
        """
        Получает все активные сессии пользователя

        Args:
            email: Email пользователя

        Returns:
            list[str]: Список активных токенов пользователя
        """
        return await self.smembers(f"sessions:{email}")

    async def save_refresh_token(self, user_id: uuid.UUID, token: str) -> None:
        """
        Сохраняет refresh токен в Redis.

        Args:
            user_id: ID пользователя
            token: Refresh токен

        Returns:
            None
        """
        # Ключ для хранения всех refresh токенов пользователя
        key = f"user:{user_id}:refresh_tokens"

        # Добавляем токен в множество
        await self.sadd(key, token)

        # Устанавливаем TTL для ключа
        await self.set_expire(key, settings.REFRESH_TOKEN_MAX_AGE)

    async def check_refresh_token(self, user_id: uuid.UUID, token: str) -> bool:
        """
        Проверяет существование refresh токена в Redis.

        Args:
            user_id: ID пользователя
            token: Refresh токен

        Returns:
            bool: True, если токен существует, иначе False
        """
        key = f"user:{user_id}:refresh_tokens"

        # Проверяем наличие токена в множестве
        result = await self.sismember(key, token)
        return bool(result)

    async def remove_refresh_token(self, user_id: uuid.UUID, token: str) -> None:
        """
        Удаляет refresh токен из Redis.

        Args:
            user_id: ID пользователя
            token: Refresh токен

        Returns:
            None
        """
        key = f"user:{user_id}:refresh_tokens"

        # Удаляем токен из множества
        await self.srem(key, token)

    async def remove_all_refresh_tokens(self, user_id: uuid.UUID) -> None:
        """
        Удаляет все refresh токены пользователя из Redis.

        Args:
            user_id: ID пользователя

        Returns:
            None
        """
        key = f"user:{user_id}:refresh_tokens"

        # Удаляем ключ полностью
        await self.delete(key)

    async def invalidate_user_tokens(self, user_id: uuid.UUID) -> None:
        """
        Инвалидирует все токены пользователя при смене пароля.

        Удаляет access и refresh токены, сбрасывает online статус.
        Используется при смене пароля для безопасности - пользователь
        должен авторизоваться заново со всех устройств.

        Args:
            user_id: UUID пользователя

        Returns:
            None

        Example:
            >>> await redis_manager.invalidate_user_tokens(user.id)
            # Все сессии пользователя завершены
        """
        logger.info("Инвалидация всех токенов для пользователя: %s", user_id)

        try:
            # 1. Удаляем все refresh токены
            await self.remove_all_refresh_tokens(user_id)

            # 2. Используем SCAN для безопасного обхода всех ключей token:*
            # (KEYS блокирует Redis, SCAN работает курсорами и не блокирует)
            cursor = 0
            while True:
                cursor, keys = await self.scan(cursor, match="token:*", count=100)

                # 3. Проверяем каждый токен - если принадлежит пользователю, удаляем
                for key in keys:
                    token = key.decode().split(":", 1)[1]
                    user_data = await self.get(f"token:{token}")

                    if user_data:
                        user = UserSchema.model_validate_json(user_data)
                        if str(user.id) == str(user_id):
                            await self.delete(f"token:{token}")
                            # Удаляем last_activity для токена
                            await self.delete(f"last_activity:{token}")

                # Выход из цикла когда cursor вернулся к 0
                if cursor == 0:
                    break

            # 4. Сбрасываем online статус
            await self.set_online_status(user_id, False)

            logger.info("Все токены пользователя успешно инвалидированы: %s", user_id)

        except Exception as e:
            logger.error(
                "Ошибка при инвалидации токенов пользователя: %s",
                str(e),
                exc_info=True,
                extra={"user_id": user_id},
            )
            # Не прерываем выполнение - важнее сохранить новый пароль

    async def save_reset_token(
        self, user_id: UUID, token: str, ttl: int = 1800
    ) -> None:
        """
        Сохраняет токен сброса пароля в Redis.

        Токен связывается с user_id и автоматически удаляется через TTL.

        Args:
            user_id: ID пользователя.
            token: Токен для сброса пароля.
            ttl: Время жизни токена в секундах (по умолчанию 1800 = 30 минут).

        Returns:
            None

        Example:
            >>> await redis_manager.save_reset_token(user_id, reset_token)
            >>> # Токен хранится 30 минут, после чего автоматически удаляется
        """
        try:
            await self.set(key=f"password_reset:{token}", value=str(user_id), ttl=ttl)
            logger.debug(
                "Токен сброса пароля сохранен в Redis",
                extra={"user_id": user_id, "ttl": ttl},
            )
        except Exception as e:
            logger.error(
                "Ошибка при сохранении токена сброса пароля: %s",
                str(e),
                exc_info=True,
                extra={"user_id": user_id},
            )
            raise

    async def get_reset_token_user(self, token: str) -> UUID | None:
        """
        Получает user_id по токену сброса пароля из Redis.

        Args:
            token: Токен сброса пароля.

        Returns:
            UUID пользователя или None, если токен не найден или истек.

        Example:
            >>> user_id = await redis_manager.get_reset_token_user(token)
            >>> if user_id:
            ...     # Токен валиден, можно сбросить пароль
        """
        try:
            user_id_str = await self.get(f"password_reset:{token}")
            if user_id_str:
                logger.debug("Токен сброса найден в Redis")
                return UUID(
                    user_id_str.decode()
                    if isinstance(user_id_str, bytes)
                    else user_id_str
                )
            logger.debug("Токен сброса не найден в Redis")
            return None
        except Exception as e:
            logger.error(
                "Ошибка при получении user_id по токену сброса: %s",
                str(e),
                exc_info=True,
            )
            return None

    async def delete_reset_token(self, token: str) -> None:
        """
        Удаляет токен сброса пароля из Redis.

        Используется после успешного сброса пароля, чтобы токен нельзя было использовать повторно.

        Args:
            token: Токен сброса пароля.

        Returns:
            None

        Example:
            >>> await redis_manager.delete_reset_token(token)
            >>> # Токен больше не действителен
        """
        try:
            await self.delete(f"password_reset:{token}")
            logger.debug("Токен сброса пароля удален из Redis")
        except Exception as e:
            logger.error(
                "Ошибка при удалении токена сброса пароля: %s", str(e), exc_info=True
            )
            # Не выбрасываем исключение - важнее успешно сменить пароль
