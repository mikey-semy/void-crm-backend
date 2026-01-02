"""
Модуль аутентификации и авторизации пользователей.

Этот модуль предоставляет компоненты для проверки подлинности
и авторизации пользователей в приложении FastAPI с использованием
JWT токенов.

Основные компоненты:
- OAuth2PasswordBearer: схема безопасности для документации OpenAPI
- get_current_user: функция-зависимость для получения текущего пользователя

Примеры использования:

1. В маршрутах FastAPI с использованием стандартных зависимостей:
    ```
    @router.get("/protected")
    async def protected_route(user: CurrentUserSchema = Depends(get_current_user)):
        return {"message": f"Hello, {user.username}!"}
    ```
"""

import logging
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer

from app.core.exceptions import (
    ForbiddenError,
    InvalidCredentialsError,
    TokenError,
    TokenInvalidError,
    TokenMissingError,
)
from app.core.security.token_manager import TokenManager
from app.schemas import UserCurrentSchema

logger = logging.getLogger(__name__)

# Создаем экземпляр OAuth2PasswordBearer для использования с Depends
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    scheme_name="OAuth2PasswordBearer",
    description="Bearer token",
    auto_error=False,
)


class AuthenticationManager:
    """
    Менеджер аутентификации пользователей.

    Этот класс предоставляет методы для работы с аутентификацией,
    включая проверку токенов и получение данных текущего пользователя.

    Методы:
        get_current_user: Получает данные текущего пользователя по токену
        extract_token_from_request: Извлекает токен из запроса (заголовок или cookies)
    """

    @staticmethod
    def extract_token_from_request(request: Request, header_token: str = None) -> str:
        """
        Извлекает токен из запроса - сначала из заголовка Authorization, затем из cookies.

        Args:
            request: Запрос FastAPI, содержащий заголовки HTTP и cookies
            header_token: Токен из заголовка Authorization (если есть)

        Returns:
            str: Найденный токен

        Raises:
            TokenMissingError: Если токен не найден ни в заголовке, ни в cookies
        """
        # Сначала пробуем получить токен из заголовка Authorization
        if header_token:
            logger.debug("Токен найден в заголовке Authorization")
            return header_token

        # Если токена нет в заголовке, проверяем cookies
        access_token_cookie = request.cookies.get("access_token")

        if access_token_cookie:
            logger.debug("Токен найден в cookies")
            return access_token_cookie

        # Если токен не найден ни в заголовке, ни в cookies
        logger.debug("Токен не найден ни в заголовке Authorization, ни в cookies")
        raise TokenMissingError()

    @staticmethod
    async def get_current_user(
        request: Request,
        token: str = Depends(oauth2_scheme),
    ) -> UserCurrentSchema:
        """
        Получает данные текущего аутентифицированного пользователя.

        Эта функция проверяет JWT токен, переданный в заголовке Authorization или cookies,
        декодирует его, и получает пользователя из системы по идентификатору
        в токене (sub).

        Args:
            request: Запрос FastAPI, содержащий заголовки HTTP и cookies
            token: Токен доступа, извлекаемый из заголовка Authorization (может быть None)

        Returns:
            UserCurrentSchema: Схема данных текущего пользователя

        Raises:
            TokenInvalidError: Если токен отсутствует, недействителен или истек
        """
        # Импортируем внутри функции чтобы избежать циклического импорта
        from app.core.connections.database import (
            get_db_session,  # ✅ Из connections, не dependencies!
        )
        from app.core.integrations.cache.auth import AuthRedisManager
        from app.repository.v1.users import UserRepository

        logger.debug(
            "Обработка запроса аутентификации с заголовками: %s", request.headers
        )
        logger.debug("Начало получения данных пользователя")
        logger.debug(
            "Получен токен из заголовка: %s", token[:50] + "..." if token else "None"
        )

        try:
            # Извлекаем токен из запроса (заголовок или cookies)
            actual_token = AuthenticationManager.extract_token_from_request(
                request, token
            )
            logger.debug(
                "Используемый токен: %s",
                actual_token[:50] + "..." if actual_token else "None",
            )

            # Проверяем и декодируем токен
            payload = TokenManager.decode_token(actual_token)

            # Валидируем payload и получаем email
            user_email = payload.get("email")
            if not user_email:
                logger.warning("Email не найден в payload токена")
                raise TokenInvalidError()

            # Получаем Redis через utility function
            from app.core.connections.cache import get_redis_client

            logger.debug("🔍 [AUTH] Перед получением Redis клиента")
            redis = await get_redis_client()
            logger.debug("🔍 [AUTH] Redis клиент получен успешно")

            redis_manager = AuthRedisManager(redis)

            # Проверяем, что токен существует в Redis (не в blacklist)
            logger.debug("🔍 [AUTH] Проверка токена в Redis...")
            cached_user = await redis_manager.get_user_by_token(actual_token)
            if not cached_user:
                logger.warning("Токен не найден в Redis (blacklist или истек)")
                raise TokenInvalidError()
            logger.debug("🔍 [AUTH] Токен найден в Redis")

            # Получаем пользователя из БД через async for (как было раньше)
            logger.debug("🔍 [AUTH] Начинаем async for session in get_db_session()...")
            async for session in get_db_session():
                logger.debug("🔍 [AUTH] Внутри async for - сессия получена")
                repository = UserRepository(session)
                logger.debug(
                    "🔍 [AUTH] UserRepository создан, вызываем get_user_by_identifier..."
                )

                # Роли и компания загружаются автоматически через default_options
                user_model = await repository.get_user_by_identifier(user_email)
                logger.debug("🔍 [AUTH] get_user_by_identifier вернул результат")

                if not user_model:
                    logger.warning("Пользователь с email %s не найден", user_email)
                    raise InvalidCredentialsError()

                # Проверяем активность пользователя
                if not user_model.is_active:
                    logger.warning(
                        "Попытка доступа с неактивным аккаунтом: %s", user_email
                    )
                    raise InvalidCredentialsError()

                # Создаем схему текущего пользователя
                # ✅ user.role использует eager-loaded user_roles relationship (не lazy load!)
                logger.debug("🔍 [AUTH] Создаем UserCurrentSchema...")
                current_user = UserCurrentSchema(
                    id=user_model.id,
                    username=user_model.username,
                    email=user_model.email,
                    role=user_model.role,  # ✅ Eager-loaded, не вызывает доп. запрос
                )
                logger.debug("🔍 [AUTH] UserCurrentSchema создан успешно")

                logger.debug(
                    "Пользователь успешно аутентифицирован: %s", current_user.username
                )
                return current_user

        except TokenError:
            # Перехватываем все ошибки токенов и пробрасываем дальше
            raise
        except Exception as e:
            logger.error("Ошибка при аутентификации: %s", str(e), exc_info=True)
            raise TokenInvalidError() from e

    @staticmethod
    def verify_api_key(request: Request) -> bool:
        """
        Проверяет API Key из заголовка X-API-Key.

        Используется для service-to-service авторизации (внешние админки).

        Args:
            request: Запрос FastAPI

        Returns:
            bool: True если API Key валидный

        Raises:
            TokenMissingError: Если API Key не передан
            InvalidCredentialsError: Если API Key невалидный
        """
        from app.core.settings import settings

        api_key = request.headers.get("X-API-Key")

        if not api_key:
            logger.debug("API Key не найден в заголовке X-API-Key")
            return False

        expected_key = settings.ADMIN_API_KEY
        if not expected_key:
            logger.warning("ADMIN_API_KEY не настроен в settings")
            return False

        if api_key != expected_key.get_secret_value():
            logger.warning("Невалидный API Key")
            raise InvalidCredentialsError()

        logger.debug("API Key успешно проверен")
        return True


async def get_current_user_or_api_key(
    request: Request,
    token: str = Depends(oauth2_scheme),
) -> UserCurrentSchema | None:
    """
    Альтернативная зависимость: проверяет JWT токен ИЛИ API Key.

    Если передан валидный API Key - возвращает None (авторизация через ключ).
    Если передан JWT токен - возвращает пользователя.
    Если ничего не передано - выбрасывает ошибку.

    Args:
        request: Запрос FastAPI
        token: Токен из заголовка Authorization (может быть None)

    Returns:
        UserCurrentSchema | None: Пользователь или None (для API Key)

    Raises:
        TokenMissingError: Если не передан ни токен, ни API Key
    """
    # Сначала проверяем API Key
    try:
        if AuthenticationManager.verify_api_key(request):
            logger.debug("Авторизация через API Key успешна")
            return None
    except InvalidCredentialsError:
        raise

    # Если API Key не передан, пробуем JWT
    return await AuthenticationManager.get_current_user(request, token)


# Wrapper функция больше не нужна - используем метод напрямую
get_current_user = AuthenticationManager.get_current_user

# Type annotation для dependency injection
CurrentUserDep = Annotated[UserCurrentSchema, Depends(get_current_user)]

# Dependency для роутов с поддержкой API Key
CurrentUserOrApiKeyDep = Annotated[
    UserCurrentSchema | None, Depends(get_current_user_or_api_key)
]


async def get_current_admin(
    current_user: CurrentUserDep,
) -> UserCurrentSchema:
    """
    Зависимость для получения текущего администратора.

    Проверяет, что текущий пользователь имеет роль "admin".
    Используется для защиты админских роутеров.

    Args:
        current_user: Текущий аутентифицированный пользователь.

    Returns:
        UserCurrentSchema: Данные текущего администратора.

    Raises:
        ForbiddenError: Если пользователь не является администратором.
    """
    if current_user.role != "admin":
        logger.warning(
            "Попытка доступа к админскому ресурсу без роли admin: %s (role=%s)",
            current_user.email,
            current_user.role,
        )
        raise ForbiddenError(detail="Доступ только для администраторов")
    return current_user


# Dependency для админских роутеров - проверяет роль admin
CurrentAdminDep = Annotated[UserCurrentSchema, Depends(get_current_admin)]
