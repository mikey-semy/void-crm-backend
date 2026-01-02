"""
Сервис для аутентификации пользователей.

Предоставляет методы для:
- Аутентификации пользователей (admin/user)
- Обновления токенов (refresh)
- Выхода из системы (logout)
- Получения текущего пользователя (me)
- Работы с токенами через Redis
"""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    InvalidCredentialsError,
    InvalidCurrentPasswordError,
    InvalidResetTokenError,
    PasswordChangeFailedError,
    ResetTokenExpiredError,
    TokenExpiredError,
    TokenInvalidError,
    TokenMissingError,
    UserInactiveError,
    UserNotFoundError,
    WeakPasswordError,
)

from app.core.security import CookieManager, PasswordManager, TokenManager
from app.models.v1.users import UserModel
from app.repository.v1.users import UserRepository
from app.schemas.v1.auth.base import (
    LogoutDataSchema,
    UserCredentialsSchema,
    UserCurrentSchema,
)
from app.schemas.v1.auth.requests import AuthSchema
from app.schemas.v1.auth.responses import (
    CurrentUserResponseSchema,
    LogoutResponseSchema,
    TokenResponseSchema,
)
from app.services.base import BaseService
from app.services.v1.token import TokenService


class AuthService(BaseService):
    """
    Сервис для аутентификации пользователей.

    Обрабатывает аутентификацию для всех ролей (admin/user) через JWT токены.
    Поддерживает хранение токенов в заголовках и cookies.

    Attributes:
        repository: Репозиторий для работы с UserModel.
        token_service: Сервис для работы с токенами.
        redis_manager: Менеджер для работы с токенами в Redis.
        rabbitmq_client: Клиент RabbitMQ для отправки email уведомлений.
    """

    def __init__(self, session: AsyncSession, token_service: TokenService):
        """
        Инициализация сервиса аутентификации.

        Args:
            session: Асинхронная сессия базы данных.
            token_service: Сервис для работы с токенами.
        """
        super().__init__(session)
        self.token_service = token_service
        self.repository = UserRepository(session=session)
        self.redis_manager = token_service.redis_manager

    # ==================== АУТЕНТИФИКАЦИЯ ====================

    async def authenticate(
        self,
        form_data: OAuth2PasswordRequestForm,
        response: Response | None = None,
        use_cookies: bool = False,
    ) -> TokenResponseSchema:
        """
        Аутентифицирует пользователя по email и паролю.

        Поддерживает все роли (admin/user). Проверяет активность аккаунта,
        генерирует JWT токены, устанавливает online статус в Redis.

        Args:
            form_data: Данные для аутентификации (email, password).
            response: HTTP ответ для установки куков (опционально).
            use_cookies: Использовать ли куки для хранения токенов.

        Returns:
            TokenResponseSchema: Токены доступа и обновления.

        Raises:
            InvalidCredentialsError: Если email или пароль неверные.
            UserInactiveError: Если аккаунт деактивирован.
        """
        self.logger.info("Попытка аутентификации пользователя: %s", form_data.username)

        # 1. Валидация и получение пользователя
        user_model, credentials = await self._validate_and_get_user(form_data)

        # 2. Проверка пароля
        await self._check_user_password(user_model, credentials)

        # 3. Проверка активности
        if not user_model.is_active:
            self.logger.warning(
                "Попытка входа неактивного пользователя",
                extra={"user_id": user_model.id, "email": user_model.email},
            )
            raise UserInactiveError()

        # 3.5. КРИТИЧНО: Перезагружаем user с user_roles для избежания lazy load
        # Роли и компания загружаются автоматически через default_options
        user_model = await self.repository.get_item_by_id(user_model.id)
        if not user_model:
            # Не должно произойти, но на всякий случай
            self.logger.error(
                "Не удалось перезагрузить пользователя с ролями",
                extra={"user_id": user_model.id},
            )
            raise InvalidCredentialsError()

        # 4. Преобразование модели в схему с хешированным паролем
        user_schema = UserCredentialsSchema(
            id=user_model.id,
            username=user_model.username,
            email=user_model.email,
            password_hash=user_model.password_hash,
            is_active=user_model.is_active,
            full_name=user_model.full_name,  # Теперь Optional
            role=user_model.role,  # @property вызывается явно, но user_roles уже загружены
        )

        # 5. Обработка успешной аутентификации
        return await self._handle_successful_auth(user_schema, response, use_cookies)

    async def _validate_and_get_user(
        self, form_data: OAuth2PasswordRequestForm
    ) -> tuple[UserModel, AuthSchema]:
        """
        Валидирует входные данные и ищет пользователя по email.

        Args:
            form_data: Данные формы аутентификации.

        Returns:
            Tuple[UserModel, AuthSchema]: Модель пользователя и credentials.

        Raises:
            InvalidCredentialsError: Если пользователь не найден.
        """
        credentials = AuthSchema(
            username=form_data.username, password=form_data.password
        )

        identifier = credentials.username  # email, phone, or username

        self.logger.info("Поиск пользователя по идентификатору: %s", identifier)

        # Поиск по email/phone/username через get_user_by_identifier()
        user_model = await self.repository.get_user_by_identifier(identifier)

        if not user_model:
            self.logger.warning(
                "Пользователь не найден", extra={"identifier": identifier}
            )
            raise InvalidCredentialsError()

        return user_model, credentials

    async def _check_user_password(
        self, user_model: UserModel, credentials: AuthSchema
    ) -> None:
        """
        Проверяет корректность пароля пользователя.

        Args:
            user_model: Модель пользователя.
            credentials: Учетные данные пользователя.

        Raises:
            InvalidCredentialsError: Если пароль неверный.
        """
        if not PasswordManager.verify(user_model.password_hash, credentials.password):
            self.logger.warning(
                "Неверный пароль пользователя",
                extra={"identifier": credentials.username, "user_id": user_model.id},
            )
            raise InvalidCredentialsError()

    async def _handle_successful_auth(
        self,
        user_schema: UserCredentialsSchema,
        response: Response | None,
        use_cookies: bool,
    ) -> TokenResponseSchema:
        """
        Обрабатывает успешную аутентификацию пользователя.

        Args:
            user_schema: Схема пользователя.
            response: HTTP-ответ FastAPI.
            use_cookies: Использовать ли куки для токенов.

        Returns:
            TokenResponseSchema: Схема ответа с токенами.
        """
        # 1. Логируем успешную аутентификацию
        self.logger.info(
            "Аутентификация успешна",
            extra={
                "user_id": user_schema.id,
                "email": user_schema.email,
            },
        )

        # 2. Обновляем last_login_at и last_activity_at в БД
        now = datetime.now(UTC)
        await self.repository.update_item(
            user_schema.id,
            {"last_login_at": now, "last_activity_at": now}
        )

        # 3. Устанавливаем статус "онлайн"
        await self.redis_manager.set_online_status(user_schema.id, True)

        # 4. Генерируем токены
        access_token, refresh_token = await self._generate_tokens(user_schema)

        # 5. Обновляем последнюю активность в Redis
        await self.redis_manager.update_last_activity(access_token)

        # 6. Устанавливаем куки, если требуется
        if response and use_cookies:
            CookieManager.set_auth_cookies(response, access_token, refresh_token)

            return TokenResponseSchema(
                message="Аутентификация успешна",
                access_token=None,  # Токены в cookies
                refresh_token=None,
                expires_in=self.settings.ACCESS_TOKEN_MAX_AGE,
            )

        # Возвращаем токены в схеме ответа
        return TokenResponseSchema(
            message="Аутентификация успешна",
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.settings.ACCESS_TOKEN_MAX_AGE,
        )

    async def _generate_tokens(
        self, user_schema: UserCredentialsSchema
    ) -> tuple[str, str]:
        """
        Генерирует access и refresh токены через TokenService.

        Args:
            user_schema: Схема пользователя.

        Returns:
            Tuple[str, str]: Access токен, refresh токен.
        """
        access_token = await self.token_service.create_access_token(user_schema)
        refresh_token = await self.token_service.create_refresh_token(user_schema.id)
        return access_token, refresh_token

    # ==================== ОБНОВЛЕНИЕ ТОКЕНОВ ====================

    async def refresh_token(
        self,
        refresh_token: str,
        response: Response | None = None,
        use_cookies: bool = False,
    ) -> TokenResponseSchema:
        """
        Обновляет access токен с помощью refresh токена.

        Args:
            refresh_token: Refresh токен.
            response: HTTP ответ для установки куков.
            use_cookies: Использовать ли куки для токенов.

        Returns:
            TokenResponseSchema: Новые токены доступа.

        Raises:
            TokenMissingError: Если refresh токен отсутствует.
            TokenInvalidError: Если refresh токен недействителен.
            TokenExpiredError: Если refresh токен истек.
        """
        if not refresh_token:
            self.logger.warning("Попытка обновления токена без refresh token")
            raise TokenMissingError()

        try:
            # 1. Валидация refresh токена и получение пользователя
            user_model, user_id = await self._validate_and_get_user_by_refresh_token(
                refresh_token
            )

            # 2. Преобразование модели в схему
            user_schema = UserCredentialsSchema(
                id=user_model.id,
                username=user_model.username,
                email=user_model.email,
                password_hash=user_model.password_hash,
                is_active=user_model.is_active,
                full_name=user_model.full_name,  # Теперь Optional
                role=user_model.role,  # @property вызывается явно
            )

            # 3. Генерация и сохранение новых токенов
            access_token, new_refresh_token = await self._generate_and_save_new_tokens(
                user_schema, user_id, refresh_token
            )

            self.logger.info("Токены успешно обновлены", extra={"user_id": user_id})

            # 4. Установка куков, если требуется
            if response and use_cookies:
                CookieManager.set_auth_cookies(
                    response, access_token, new_refresh_token
                )

                return TokenResponseSchema(
                    message="Токен успешно обновлен",
                    access_token=None,
                    refresh_token=None,
                    expires_in=self.settings.ACCESS_TOKEN_MAX_AGE,
                )

            return TokenResponseSchema(
                message="Токен успешно обновлен",
                access_token=access_token,
                refresh_token=new_refresh_token,
                expires_in=self.settings.ACCESS_TOKEN_MAX_AGE,
            )

        except (TokenExpiredError, TokenInvalidError) as e:
            self.logger.warning(
                "Ошибка при обновлении токена: %s",
                type(e).__name__,
                extra={"error_type": type(e).__name__},
            )
            raise

    async def _validate_and_get_user_by_refresh_token(
        self, refresh_token: str
    ) -> tuple[UserModel, UUID]:
        """
        Валидирует refresh токен и получает пользователя.

        Args:
            refresh_token: Refresh токен.

        Returns:
            Tuple[UserModel, UUID]: Модель пользователя и его ID.
        """
        payload = TokenManager.decode_token(refresh_token)
        user_id = TokenManager.validate_refresh_token(payload)

        if not await self.redis_manager.check_refresh_token(user_id, refresh_token):
            self.logger.warning(
                "Попытка использовать неизвестный refresh токен",
                extra={"user_id": user_id},
            )
            raise TokenInvalidError()

        user_model = await self.repository.get_item_by_id(user_id)
        if not user_model:
            self.logger.warning(
                "Пользователь не найден при обновлении токена",
                extra={"user_id": user_id},
            )
            raise UserNotFoundError(field="id", value=str(user_id))

        return user_model, user_id

    async def _generate_and_save_new_tokens(
        self, user_schema: UserCredentialsSchema, user_id: UUID, old_refresh_token: str
    ) -> tuple[str, str]:
        """
        Генерирует и сохраняет новые access и refresh токены.

        Args:
            user_schema: Схема пользователя.
            user_id: ID пользователя.
            old_refresh_token: Старый refresh токен для удаления.

        Returns:
            Tuple[str, str]: Новый access токен и новый refresh токен.
        """
        access_token = await self.token_service.create_access_token(user_schema)
        new_refresh_token = await self.token_service.create_refresh_token(user_id)
        await self.redis_manager.remove_refresh_token(user_id, old_refresh_token)
        return access_token, new_refresh_token

    # ==================== ВЫХОД ====================

    async def logout(
        self,
        authorization: str,
        response: Response | None = None,
        clear_cookies: bool = False,
    ) -> LogoutResponseSchema:
        """
        Выход из системы с удалением токенов.

        Args:
            authorization: Bearer токен из заголовка.
            response: HTTP ответ для очистки куков.
            clear_cookies: Очистить ли cookies при выходе.

        Returns:
            LogoutResponseSchema: Информация о выходе.

        Raises:
            TokenMissingError: Если токен отсутствует.
        """
        if not authorization:
            self.logger.warning("Попытка выхода без access token")
            raise TokenMissingError()

        token = TokenManager.get_token_from_header(authorization)

        # Удаление токена из Redis
        await self.redis_manager.remove_token(token)

        # Очистка куков, если требуется
        if response and clear_cookies:
            CookieManager.clear_auth_cookies(response)

        self.logger.info("Пользователь вышел из системы")

        return LogoutResponseSchema(
            success=True,
            message="Выход выполнен успешно",
            data=LogoutDataSchema(logged_out_at=datetime.now(UTC)),
        )

    # ==================== ТЕКУЩИЙ ПОЛЬЗОВАТЕЛЬ ====================

    async def get_current_user(
        self,
        authorization: str,
    ) -> CurrentUserResponseSchema:
        """
        Получает информацию о текущем аутентифицированном пользователе.

        Args:
            authorization: Bearer токен из заголовка.

        Returns:
            CurrentUserResponseSchema: Данные текущего пользователя.

        Raises:
            TokenMissingError: Если токен отсутствует.
            TokenInvalidError: Если токен недействителен.
        """
        if not authorization:
            self.logger.warning("Попытка получить текущего пользователя без токена")
            raise TokenMissingError()

        token = TokenManager.get_token_from_header(authorization)

        # Получение пользователя по токену
        user_data = await self.redis_manager.get_user_by_token(token)

        if not user_data:
            self.logger.warning("Пользователь не найден по токену")
            raise TokenInvalidError()

        # Конвертация в CurrentUserSchema
        current_user = UserCurrentSchema(
            id=user_data.id,
            username=user_data.username
            if hasattr(user_data, "username")
            else user_data.email.split("@")[0],
            email=user_data.email,
            full_name=user_data.full_name if hasattr(user_data, "full_name") else None,
            role=user_data.role if hasattr(user_data, "role") else "user",
        )

        return CurrentUserResponseSchema(success=True, message=None, data=current_user)

    # ==================== СМЕНА ПАРОЛЯ ====================

    async def change_password(
        self,
        user_id: UUID,
        old_password: str,
        new_password: str,
    ) -> UserModel:
        """
        Изменяет пароль авторизованного пользователя.

        Проверяет текущий пароль, валидирует новый, обновляет хеш в базе,
        инвалидирует все токены пользователя через Redis.

        Args:
            user_id: UUID пользователя, который меняет пароль.
            old_password: Текущий пароль для подтверждения.
            new_password: Новый пароль (будет провалидирован и захеширован).

        Returns:
            UserModel: Обновленная модель пользователя.

        Raises:
            UserNotFoundError: Если пользователь не найден.
            InvalidCurrentPasswordError: Если текущий пароль неверен.
            WeakPasswordError: Если новый пароль не соответствует требованиям.
            PasswordChangeFailedError: Если произошла ошибка при сохранении.

        Example:
            >>> user = await auth_service.change_password(
            ...     user_id=user.id,
            ...     old_password="OldPass123!",
            ...     new_password="NewPass456@"
            ... )
        """
        self.logger.info("Начало процесса смены пароля для пользователя: %s", user_id)

        try:
            # 1. Получаем пользователя
            user = await self.repository.get_item_by_id(user_id)
            if not user:
                self.logger.warning("Пользователь не найден: %s", user_id)
                raise UserNotFoundError(user_id=user_id)

            # 2. Проверяем текущий пароль
            if not PasswordManager.verify(user.password_hash, old_password):
                self.logger.warning(
                    "Неверный текущий пароль при смене", extra={"user_id": user_id}
                )
                raise InvalidCurrentPasswordError()

            # 3. Валидируем новый пароль
            from app.core.utils import validate_password_strength

            try:
                validate_password_strength(new_password)
            except ValueError as e:
                self.logger.warning(
                    "Слабый пароль при смене: %s", str(e), extra={"user_id": user_id}
                )
                raise WeakPasswordError(detail=str(e)) from e

            # 4. Хешируем новый пароль
            new_password_hash = PasswordManager.hash_password(new_password)

            # 5. Обновляем пароль в базе данных
            update_data = {"password_hash": new_password_hash}
            updated_user = await self.repository.update_item(user_id, update_data)

            if not updated_user:
                self.logger.error(
                    "Не удалось обновить пароль в БД", extra={"user_id": user_id}
                )
                raise PasswordChangeFailedError()

            # 6. Инвалидируем все токены пользователя
            await self.redis_manager.invalidate_user_tokens(user_id)

            self.logger.info("Пароль успешно изменен для пользователя: %s", user_id)

            return updated_user

        except (UserNotFoundError, InvalidCurrentPasswordError, WeakPasswordError):
            # Пробрасываем domain exceptions дальше (обработает global handler)
            raise

        except Exception as e:
            # Все остальных ошибки логируем и оборачиваем
            self.logger.error(
                "Неожиданная ошибка при смене пароля: %s",
                str(e),
                exc_info=True,
                extra={"user_id": user_id},
            )
            raise PasswordChangeFailedError(
                detail=f"Произошла ошибка при смене пароля: {str(e)}"
            ) from e

    # ==================== PASSWORD RESET ====================

    async def request_password_reset(self, email: str) -> dict:
        """
        Запрос на сброс пароля.

        Генерирует токен сброса пароля и сохраняет его в Redis.
        Из соображений безопасности всегда возвращает успех, даже если email не найден.

        Args:
            email: Email пользователя для сброса пароля.

        Returns:
            dict: Данные для ответа (email, expires_in).

        Raises:
            Exception: При ошибке создания токена или сохранения в Redis.

        Example:
            >>> result = await auth_service.request_password_reset("user@example.com")
            >>> # Возвращает {"email": "user@example.com", "expires_in": 1800}
        """
        self.logger.info("Запрос на сброс пароля", extra={"email": email})

        try:
            # 1. Проверяем существование пользователя
            user = await self.repository.get_item_by_field("email", email)

            # 2. Из соображений безопасности всегда возвращаем успех
            # (чтобы не раскрывать, зарегистрирован email или нет)
            if not user:
                self.logger.warning(
                    "Пользователь с email не найден (не раскрываем в ответе)",
                    extra={"email": email},
                )
                # Возвращаем успешный ответ для безопасности
                return {
                    "email": email,
                    "expires_in": self.settings.PASSWORD_RESET_TOKEN_TTL,
                }

            # 3. Генерируем токен сброса пароля
            reset_token = TokenManager.generate_password_reset_token(user.id)

            # 4. Сохраняем токен в Redis с TTL из настроек
            await self.redis_manager.save_reset_token(
                user.id, reset_token, ttl=self.settings.PASSWORD_RESET_TOKEN_TTL
            )

            self.logger.info(
                "Токен сброса пароля создан", extra={"user_id": user.id, "email": email}
            )

            return {
                "email": email,
                "expires_in": self.settings.PASSWORD_RESET_TOKEN_TTL,
            }

        except Exception as e:
            self.logger.error(
                "Ошибка при запросе сброса пароля: %s",
                str(e),
                exc_info=True,
                extra={"email": email},
            )
            raise

    async def confirm_password_reset(self, token: str, new_password: str) -> UserModel:
        """
        Подтверждение сброса пароля по токену.

        Проверяет токен, валидирует новый пароль, обновляет в БД и инвалидирует все токены.

        Args:
            token: Токен сброса пароля из email.
            new_password: Новый пароль пользователя.

        Returns:
            UserModel: Обновленная модель пользователя.

        Raises:
            InvalidResetTokenError: Если токен не найден или невалиден.
            ResetTokenExpiredError: Если токен истек.
            UserNotFoundError: Если пользователь не найден.
            WeakPasswordError: Если новый пароль не соответствует требованиям.
            PasswordChangeFailedError: При ошибке обновления пароля.

        Example:
            >>> user = await auth_service.confirm_password_reset(token, "NewPass123!")
            >>> # Пароль изменен, все сессии завершены
        """

        self.logger.info("Подтверждение сброса пароля")

        try:
            # 1. Декодируем и валидируем токен
            try:
                payload = TokenManager.decode_token(token)
            except TokenExpiredError:
                self.logger.warning("Токен сброса пароля истек")
                raise ResetTokenExpiredError() from None
            except (TokenInvalidError, Exception):
                self.logger.warning("Невалидный токен сброса пароля")
                raise InvalidResetTokenError() from None

            # 2. Проверяем тип токена
            if payload.get("type") != "password_reset":
                self.logger.warning(
                    "Неверный тип токена", extra={"type": payload.get("type")}
                )
                raise InvalidResetTokenError(detail="Неверный тип токена")

            # 3. Получаем user_id из Redis (проверка, что токен не использован)
            user_id_str = payload.get("sub")
            if not user_id_str:
                self.logger.warning("Отсутствует sub в payload токена")
                raise InvalidResetTokenError(detail="Некорректный токен")

            user_id = UUID(user_id_str)

            # Проверяем, что токен есть в Redis (не истек и не использован)
            stored_user_id = await self.redis_manager.get_reset_token_user(token)
            if not stored_user_id or str(stored_user_id) != str(user_id):
                self.logger.warning("Токен не найден в Redis или не совпадает user_id")
                raise InvalidResetTokenError(detail="Токен уже использован или истек")

            # 4. Получаем пользователя
            user = await self.repository.get_item_by_id(user_id)
            if not user:
                self.logger.warning(
                    "Пользователь не найден", extra={"user_id": user_id}
                )
                raise UserNotFoundError(user_id=user_id)

            # 5. Валидируем новый пароль
            from app.core.utils import validate_password_strength

            try:
                validate_password_strength(new_password)
            except ValueError as e:
                self.logger.warning(
                    "Новый пароль не соответствует требованиям безопасности: %s",
                    str(e),
                    extra={"user_id": user_id},
                )
                raise WeakPasswordError(detail=str(e)) from e

            # 6. Хешируем новый пароль
            new_password_hash = PasswordManager.hash_password(new_password)

            # 7. Обновляем пароль в БД
            update_data = {"password_hash": new_password_hash}
            updated_user = await self.repository.update_item(user_id, update_data)

            if not updated_user:
                self.logger.error(
                    "Не удалось обновить пароль в БД", extra={"user_id": user_id}
                )
                raise PasswordChangeFailedError()

            # 8. Удаляем токен из Redis (чтобы нельзя было использовать повторно)
            await self.redis_manager.delete_reset_token(token)

            # 9. Инвалидируем все токены пользователя
            await self.redis_manager.invalidate_user_tokens(user_id)

            self.logger.info("Пароль успешно сброшен для пользователя: %s", user_id)

            return updated_user

        except (
            InvalidResetTokenError,
            ResetTokenExpiredError,
            UserNotFoundError,
            WeakPasswordError,
        ):
            # Пробрасываем domain exceptions дальше
            raise

        except Exception as e:
            self.logger.error(
                "Неожиданная ошибка при сбросе пароля: %s", str(e), exc_info=True
            )
            raise PasswordChangeFailedError(
                detail=f"Произошла ошибка при сбросе пароля: {str(e)}"
            ) from e
