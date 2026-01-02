"""
Роутер для работы с профилем пользователя.

Модуль предоставляет HTTP API для управления профилем текущего пользователя:
- Получение профиля (GET /users/me)
- Обновление профиля (PUT /users/me)
- Удаление аккаунта (DELETE /users/me)

Все endpoints защищены через ProtectedRouter (требуется аутентификация).
Обработка исключений: автоматическая обработка кастомных исключений из
app.core.exceptions.users через глобальный exception handler.
"""

from uuid import UUID

from fastapi import status

from app.core.dependencies import UserServiceDep
from app.core.dependencies.websocket import WebSocketManagerDep
from app.core.security import CurrentUserDep
from app.routers.base import ProtectedRouter
from app.schemas import (
    ProfileResponseSchema,
    UserDeletedSchema,
    UserDeleteResponseSchema,
    UserDetailSchema,
    UserPublicProfileResponseSchema,
    UserPublicProfileSchema,
    UserUpdateSchema,
    UsersListResponseSchema,
)


class UserRouter(ProtectedRouter):
    """
    Роутер для API профиля пользователя.

    Предоставляет HTTP API для работы с профилем текущего пользователя.
    Все endpoints защищены через CurrentUserDep (автоматически через ProtectedRouter).

    Protected Endpoints:
        GET /users/me - Получить профиль текущего пользователя
        PUT /users/me - Обновить профиль текущего пользователя
        DELETE /users/me - Удалить аккаунт (soft delete)

    Архитектурные особенности:
        - Наследуется от ProtectedRouter (все endpoints защищены)
        - CurrentUserDep доступен во всех endpoints
        - Service возвращает domain objects (UserModel)
        - Router конвертирует в Pydantic schemas
        - Global exception handler обрабатывает domain exceptions
    """

    def __init__(self):
        """Инициализирует UserRouter с префиксом и тегами."""
        super().__init__(prefix="users", tags=["Users"])

    def configure(self):
        """Настройка endpoint'ов роутера."""

        # ==================== ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ ====================

        @self.router.get(
            path="/me",
            response_model=ProfileResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""\
## 👤 Получить профиль текущего пользователя

Возвращает полные данные профиля аутентифицированного пользователя,
включая информацию о связанной компании.

### Требования:
- JWT токен в заголовке Authorization

### Returns:
- Данные профиля пользователя с информацией о компании

### Errors:
- **401** — токен отсутствует или невалиден
- **404** — пользователь не найден
""",
        )
        async def get_profile(
            service: UserServiceDep = None,
            current_user: CurrentUserDep = None,
        ) -> ProfileResponseSchema:
            """
            Получает профиль текущего пользователя.

            Args:
                service: Сервис пользователей (dependency injection)
                current_user: Текущий аутентифицированный пользователь

            Returns:
                ProfileResponseSchema: Данные профиля

            Raises:
                UserNotFoundError: Если пользователь не найден (обрабатывается глобально)
            """
            # Получаем пользователя через сервис
            user = await service.get_profile(current_user.id)

            # Конвертация SQLAlchemy model → Pydantic schema
            schema = UserDetailSchema.model_validate(user)

            return ProfileResponseSchema(
                success=True,
                message="Профиль получен",
                data=schema,
            )

        @self.router.put(
            path="/me",
            response_model=ProfileResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""\
## ✏️ Обновить профиль текущего пользователя

Позволяет пользователю обновить свои данные:
- ФИО (full_name)
- Телефон (phone)
- Должность (position)
- Email (с проверкой уникальности)

### Требования:
- JWT токен в заголовке Authorization

### Примечания:
- Email и phone проверяются на уникальность
- Защищенные поля (is_active, role, password) нельзя изменить
- Обновляются только переданные поля (partial update)

### Returns:
- Обновленные данные профиля

### Errors:
- **401** — токен отсутствует или невалиден
- **404** — пользователь не найден
- **409** — email или телефон уже заняты
""",
        )
        async def update_profile(
            update_data: UserUpdateSchema,
            service: UserServiceDep = None,
            current_user: CurrentUserDep = None,
            ws_manager: WebSocketManagerDep = None,
        ) -> ProfileResponseSchema:
            """
            Обновляет профиль текущего пользователя.

            Args:
                update_data: Данные для обновления
                service: Сервис пользователей (dependency injection)
                current_user: Текущий аутентифицированный пользователь
                ws_manager: WebSocket менеджер для уведомлений

            Returns:
                ProfileResponseSchema: Обновленные данные профиля

            Raises:
                UserNotFoundError: Если пользователь не найден
                UserEmailConflictError: Если email уже занят
                UserPhoneConflictError: Если телефон уже занят
            """
            # Обновляем через сервис (валидация уникальности внутри)
            updated_user = await service.update_profile(
                current_user.id, update_data.model_dump(exclude_unset=True)
            )

            # Конвертация SQLAlchemy model → Pydantic schema
            schema = UserDetailSchema.model_validate(updated_user)

            # Уведомляем всех клиентов об обновлении данных пользователя
            await ws_manager.notify_user_updated(
                str(current_user.id),
                {
                    "username": updated_user.username,
                    "full_name": updated_user.full_name,
                    "role": updated_user.role,
                },
            )

            return ProfileResponseSchema(
                success=True,
                message="Профиль обновлен",
                data=schema,
            )

        @self.router.delete(
            path="/me",
            response_model=UserDeleteResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""\
## 🗑️ Удалить аккаунт текущего пользователя

Деактивирует аккаунт пользователя (soft delete).
Данные сохраняются в БД для истории заказов.

### Требования:
- JWT токен в заголовке Authorization

### Примечания:
- Физического удаления не происходит
- Устанавливается is_active=False
- Пользователь больше не сможет войти в систему
- Токены автоматически инвалидируются

### Returns:
- Подтверждение удаления с email пользователя

### Errors:
- **401** — токен отсутствует или невалиден
- **404** — пользователь не найден
""",
        )
        async def delete_account(
            service: UserServiceDep = None,
            current_user: CurrentUserDep = None,
        ) -> UserDeleteResponseSchema:
            """
            Удаляет аккаунт текущего пользователя (soft delete).

            Args:
                service: Сервис пользователей (dependency injection)
                current_user: Текущий аутентифицированный пользователь

            Returns:
                UserDeleteResponseSchema: Подтверждение удаления

            Raises:
                UserNotFoundError: Если пользователь не найден
            """
            # Деактивируем через сервис
            deleted_user = await service.delete_account(current_user.id)

            # Конвертация в схему удаленного пользователя
            schema = UserDeletedSchema(
                id=deleted_user.id,
                email=deleted_user.email,
                deleted_at=deleted_user.updated_at,
            )

            return UserDeleteResponseSchema(
                success=True,
                message="Аккаунт деактивирован",
                data=schema,
            )

        # ==================== СПИСОК ПОЛЬЗОВАТЕЛЕЙ ====================

        @self.router.get(
            path="",
            response_model=UsersListResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""\
## 👥 Получить список всех пользователей

Возвращает список всех активных пользователей системы.

### Требования:
- JWT токен в заголовке Authorization

### Returns:
- Список пользователей с публичной информацией

### Errors:
- **401** — токен отсутствует или невалиден
""",
        )
        async def get_all_users(
            service: UserServiceDep = None,
            current_user: CurrentUserDep = None,
        ) -> UsersListResponseSchema:
            """
            Получает список всех активных пользователей.

            Args:
                service: Сервис пользователей (dependency injection)
                current_user: Текущий аутентифицированный пользователь

            Returns:
                UsersListResponseSchema: Список пользователей
            """
            users = await service.get_all_users()

            schemas = [UserPublicProfileSchema.model_validate(user) for user in users]

            return UsersListResponseSchema(
                success=True,
                message="Список пользователей получен",
                data=schemas,
            )

        # ==================== ПУБЛИЧНЫЙ ПРОФИЛЬ ====================

        @self.router.get(
            path="/{user_id}",
            response_model=UserPublicProfileResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""\
## 👤 Получить публичный профиль пользователя

Возвращает публичную информацию о пользователе по его ID.
Доступно только для аутентифицированных пользователей.

### Требования:
- JWT токен в заголовке Authorization

### Returns:
- Публичные данные профиля пользователя (без email, телефона и т.д.)

### Errors:
- **401** — токен отсутствует или невалиден
- **404** — пользователь не найден
""",
        )
        async def get_user_profile(
            user_id: UUID,
            service: UserServiceDep = None,
            current_user: CurrentUserDep = None,
        ) -> UserPublicProfileResponseSchema:
            """
            Получает публичный профиль пользователя по ID.

            Args:
                user_id: UUID пользователя для просмотра
                service: Сервис пользователей (dependency injection)
                current_user: Текущий аутентифицированный пользователь

            Returns:
                UserPublicProfileResponseSchema: Публичные данные профиля

            Raises:
                UserNotFoundError: Если пользователь не найден
            """
            # Получаем пользователя через сервис
            user = await service.get_profile(user_id)

            # Конвертация SQLAlchemy model → Pydantic schema (публичная версия)
            schema = UserPublicProfileSchema.model_validate(user)

            return UserPublicProfileResponseSchema(
                success=True,
                message="Профиль получен",
                data=schema,
            )
