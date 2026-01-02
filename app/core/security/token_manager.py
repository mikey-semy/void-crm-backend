"""
Библиотека методов TokenManager

_base_payload(token_type, expires_delta) — создаёт базовый payload с iat, exp, jti, type.
_validate_payload_structure(payload) — приватный метод для проверки структуры payload.
generate_token(payload) — кодирует JWT.
decode_token(token) — декодирует JWT.
is_expired(expires_at) — проверяет, истёк ли токен.
_validate_required_keys(payload) — приватный метод для проверки обязательных ключей.
validate_token_payload(payload, expected_type) — проверяет payload и тип токена.
create_payload(user) — создаёт payload для access-токена.
validate_payload(payload) — проверяет access payload и возвращает email.
_validate_and_get_user_id(payload, expected_type) - приватный метод для валидации токенов с user_id.
create_refresh_payload(user_id) — создаёт payload для refresh-токена.
create_refresh_token(user_id) — генерирует JWT refresh-токен.
validate_refresh_token(payload) — проверяет refresh payload и возвращает user_id.
get_token_from_header(authorization) — извлекает JWT из заголовка Authorization.
"""

import re
import uuid
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from jose import ExpiredSignatureError, JWTError, jwt

from app.core.exceptions import (
    InvalidUserDataError,
    TokenExpiredError,
    TokenInvalidError,
    TokenMissingError,
)
from app.core.settings import settings


class TokenType(str, Enum):
    """Константы для типов токенов."""

    ACCESS = "access"
    REFRESH = "refresh"
    EMAIL_VERIFICATION = "email_verification"
    PASSWORD_RESET = "password_reset"


class TokenManager:
    """
    TokenManager для работы с JWT.

    Содержит методы:
     Генерация токена
     Декодирование токена
     Проверка токена и срока действия
     Валидация payload для разных типов токенов
     Создание токенов: access, refresh
     Извлечение токена из заголовка Authorization
    """

    @staticmethod
    def _base_payload(
        token_type: TokenType, expires_delta: timedelta
    ) -> dict[str, Any]:
        """
        Создаёт базовый payload с общими полями для всех типов токенов.

        Args:
            token_type (TokenType): Тип токена (ACCESS, REFRESH).
            expires_delta (timedelta): Время жизни токена.

        Returns:
            dict[str, Any]: Словарь с базовыми полями payload.
        """
        now = datetime.now(UTC)
        now_ts = int(now.timestamp())
        exp_ts = now_ts + int(expires_delta.total_seconds())
        return {
            "iat": now_ts,
            "expires_at": exp_ts,
            "jti": str(uuid.uuid4()),
            "type": token_type.value,
        }

    @staticmethod
    def _validate_payload_structure(payload: dict) -> None:
        """
        Приватный метод для проверки, что payload не пуст и имеет тип dict.

        Args:
            payload (dict): Данные токена для проверки.

        Raises:
            TokenInvalidError: Если payload пустой или не dict.
        """
        if not payload or not isinstance(payload, dict):
            raise TokenInvalidError(detail="Payload пустой или не dict")

    @staticmethod
    def generate_token(payload: dict) -> str:
        """
        Генерирует JWT токен по переданному payload.

        Args:
            payload: Данные токена.

        Returns:
            str: Закодированный JWT токен.

        Raises:
            TokenInvalidError: Если 'sub' отсутствует в payload.
            ValueError: Если алгоритм шифрования не поддерживается.
        """
        TokenManager._validate_payload_structure(payload)

        if "sub" not in payload:
            raise TokenInvalidError(detail='Payload должен содержать "sub"')

        return jwt.encode(
            payload,
            key=settings.TOKEN_SECRET_KEY.get_secret_value(),
            algorithm=settings.TOKEN_ALGORITHM,
        )

    @staticmethod
    def decode_token(token: str) -> dict:
        """
        Декодирует JWT токен и проверяет его подпись.

        Args:
            token: JWT токен в виде строки.

        Returns:
            dict: Декодированные данные токена.

        Raises:
            TokenMissingError: Если токен отсутствует.
            TokenInvalidError: Если токен некорректен или имеет неверную структуру.
            TokenExpiredError: Если подпись верна, но токен истёк.
        """
        if not token:
            raise TokenMissingError(detail="Токен отсутствует")

        try:
            payload = jwt.decode(
                token,
                key=settings.TOKEN_SECRET_KEY.get_secret_value(),
                algorithms=[settings.TOKEN_ALGORITHM],
            )
        except ExpiredSignatureError as exc:
            raise TokenExpiredError(detail="Токен просрочен") from exc
        except JWTError as exc:
            raise TokenInvalidError(detail="Некорректный токен") from exc

        TokenManager._validate_required_keys(payload)
        return payload

    @staticmethod
    def is_expired(expires_at: int, leeway_in_seconds: int = 0) -> bool:
        """
        Проверяет, истек ли срок действия токена, с учетом допуска.

        Args:
            expires_at: Дата и время окончания действия токена.
            leeway_in_seconds: Допуск в секундах.

        Returns:
            bool: True, если токен истёк, иначе False.
        """
        if expires_at is None:
            return True
        current_timestamp = int(datetime.now(UTC).timestamp())
        return current_timestamp > expires_at + leeway_in_seconds

    @staticmethod
    def _validate_required_keys(payload: dict) -> None:
        """
        Приватный метод для проверки наличия обязательных ключей в payload.

        Args:
            payload: Раскодированные данные токена.

        Raises:
            TokenInvalidError: Если 'sub' или 'expires_at' отсутствует.
        """
        TokenManager._validate_payload_structure(payload)
        if "sub" not in payload or "expires_at" not in payload:
            raise TokenInvalidError(
                detail='Структура токена не верна: отсутствуют обязательные поля "sub" или "expires_at"'
            )

    @staticmethod
    def validate_token_payload(
        payload: dict, expected_type: TokenType | None = None
    ) -> dict:
        """
        Проверяет наличие обязательных полей и тип токена в payload.

        Args:
            payload: Раскодированные данные токена.
            expected_type: Ожидаемый тип токена (TokenType.ACCESS, TokenType.REFRESH и т.д.).

        Raises:
            TokenInvalidError: Если тип токена не совпадает, payload пустой или не dict.
            TokenExpiredError: Если токен просрочен.
        """
        TokenManager._validate_payload_structure(payload)

        if expected_type:
            token_type = payload.get("type")
            if token_type != expected_type.value:
                raise TokenInvalidError(
                    detail=f"Ожидался тип токена: {expected_type.value}, получен {token_type}"
                )

        expires_at = payload.get("expires_at")
        if TokenManager.is_expired(expires_at):
            raise TokenExpiredError(detail="Токен просрочен")

        return payload

    @staticmethod
    def _validate_and_get_user_id(payload: dict, expected_type: TokenType) -> uuid.UUID:
        """
        Приватный метод для проверки и извлечения user_id из payload токенов.

        Этот метод обобщает логику для refresh, верификации и сброса пароля.

        Args:
            payload: Раскодированные данные токена.
            expected_type: Ожидаемый тип токена.

        Returns:
            uuid.UUID: ID пользователя.

        Raises:
            TokenInvalidError: Если payload некорректен, отсутствует user_id или тип токена неверный.
            TokenExpiredError: Если токен просрочен.
        """
        TokenManager.validate_token_payload(payload, expected_type=expected_type)
        user_id = payload.get("sub")
        if not user_id:
            raise TokenInvalidError(
                detail=f"Отсутствует user_id в токене типа {expected_type.value}"
            )
        return uuid.UUID(str(user_id))

    @staticmethod
    def create_payload(user: Any) -> dict:
        """
        Создает payload для access-токена.

        Args:
            user: Объект пользователя, содержащий как минимум `id` и `email`.

        Returns:
            dict: Словарь с данными токена.

        Raises:
            InvalidUserDataError: Если у объекта пользователя отсутствуют необходимые атрибуты или их значения некорректны.
        """
        required_attrs_with_types = {
            "id": (uuid.UUID, "uuid"),
            "email": (str, "string"),
        }

        for attr, (expected_type, type_name) in required_attrs_with_types.items():
            if not hasattr(user, attr):
                raise InvalidUserDataError(
                    detail=f"Объект пользователя должен содержать атрибут `{attr}`"
                )
            value = getattr(user, attr)
            if not isinstance(value, expected_type):
                raise InvalidUserDataError(
                    detail=f"Атрибут `{attr}` должен быть типа `{type_name}`"
                )
            if attr == "email" and not re.match(r"[^@]+@[^@]+\.[^@]+", value):
                raise InvalidUserDataError(
                    detail="Атрибут `email` имеет неверный формат"
                )

        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = TokenManager._base_payload(TokenType.ACCESS, expires_delta)
        payload.update(
            {
                "sub": str(user.id),
                "email": user.email,
            }
        )
        return payload

    @staticmethod
    def validate_payload(payload: dict) -> str:
        """
        Проверяет и извлекает email из payload access-токена.

        Args:
            payload: Раскодированные данные токена.

        Returns:
            str: Email пользователя.

        Raises:
            TokenInvalidError: Если payload некорректен или отсутствует email.
            TokenExpiredError: Если access токен просрочен.
        """
        TokenManager.validate_token_payload(payload, expected_type=TokenType.ACCESS)
        email = payload.get("email")
        if not email:
            raise TokenInvalidError(detail="Отсутствует email в payload токена")
        return email

    @staticmethod
    def create_refresh_payload(user_id: int | str | uuid.UUID) -> dict:
        """
        Создает payload для refresh-токена.

        Args:
            user_id (Union[int, str, uuid.UUID]): ID пользователя.

        Returns:
            dict: Данные токена с типом 'refresh', временем создания, временем истечения и jti.
        """
        expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        payload = TokenManager._base_payload(TokenType.REFRESH, expires_delta)
        payload.update({"sub": str(user_id)})
        return payload

    @staticmethod
    def create_refresh_token(user_id: int | str | uuid.UUID) -> str:
        """
        Генерирует refresh-токен на основе payload.

        Args:
            user_id (Union[int, str, uuid.UUID]): ID пользователя.

        Returns:
            str: JWT refresh-токен в виде строки.
        """
        payload = TokenManager.create_refresh_payload(user_id)
        return TokenManager.generate_token(payload)

    @staticmethod
    def validate_refresh_token(payload: dict) -> uuid.UUID:
        """
        Проверяет payload refresh-токена и извлекает user_id.

        Args:
            payload: Раскодированные данные токена.

        Returns:
            uuid.UUID: ID пользователя.

        Raises:
            TokenInvalidError: Если payload некорректен, отсутствует user_id или тип токена неверный.
            TokenExpiredError: Если refresh токен просрочен.
        """
        return TokenManager._validate_and_get_user_id(payload, TokenType.REFRESH)

    @staticmethod
    def generate_password_reset_token(user_id: int | uuid.UUID) -> str:
        """
        Генерирует токен для сброса пароля.

        Создает JWT токен с типом 'password_reset', который действует 30 минут.
        Токен содержит user_id для идентификации пользователя при подтверждении сброса.

        Args:
            user_id: ID пользователя (int или UUID).

        Returns:
            str: JWT токен для сброса пароля.

        Example:
            >>> token = TokenManager.generate_password_reset_token(user_id)
            >>> # Токен отправляется в email и используется для подтверждения
        """
        expires_delta = timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
        payload = TokenManager._base_payload(TokenType.PASSWORD_RESET, expires_delta)
        payload.update({"sub": str(user_id)})
        return TokenManager.generate_token(payload)

    @staticmethod
    def validate_password_reset_token(payload: dict) -> uuid.UUID:
        """
        Проверяет payload токена сброса пароля и извлекает user_id.

        Args:
            payload: Раскодированные данные токена.

        Returns:
            uuid.UUID: ID пользователя.

        Raises:
            TokenInvalidError: Если payload некорректен, отсутствует user_id или тип токена неверный.
            TokenExpiredError: Если токен сброса пароля просрочен.
        """
        return TokenManager._validate_and_get_user_id(payload, TokenType.PASSWORD_RESET)

    @staticmethod
    def generate_verification_token(user_id: int | uuid.UUID) -> str:
        """
        Генерирует токен для верификации email.

        Создает JWT токен с типом 'email_verification', который действует 24 часа.
        Токен содержит user_id для идентификации пользователя при подтверждении email.

        Args:
            user_id: ID пользователя (int или UUID).

        Returns:
            str: JWT токен для верификации email.

        Example:
            >>> token = TokenManager.generate_verification_token(user_id)
            >>> # Токен отправляется в email и используется для подтверждения
        """
        expires_delta = timedelta(minutes=settings.VERIFICATION_TOKEN_EXPIRE_MINUTES)
        payload = TokenManager._base_payload(
            TokenType.EMAIL_VERIFICATION, expires_delta
        )
        payload.update({"sub": str(user_id)})
        return TokenManager.generate_token(payload)

    @staticmethod
    def validate_verification_token(payload: dict) -> uuid.UUID:
        """
        Валидирует токен верификации email.

        Args:
            payload: Данные из токена

        Returns:
            uuid.UUID: ID пользователя

        Raises:
            TokenInvalidError: Если тип токена неверный
            TokenExpiredError: Если токен истек
        """
        return TokenManager._validate_and_get_user_id(
            payload, TokenType.EMAIL_VERIFICATION
        )

    @staticmethod
    def get_token_from_header(authorization: str) -> str:
        """
        Извлекает JWT токен из заголовка Authorization.

        Args:
            authorization: Строка заголовка в формате 'Bearer <token>'.

        Returns:
            str: JWT токен.

        Raises:
            TokenMissingError: Если заголовок Authorization отсутствует или токен пуст.
            TokenInvalidError: Если формат заголовка некорректен.
        """
        if not authorization:
            raise TokenMissingError(detail="Токен отсутствует")

        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
            raise TokenInvalidError(
                detail='Неправильный формат Authorization. Ожидается "Bearer <token>"'
            )

        token = parts[1].strip()
        return token
