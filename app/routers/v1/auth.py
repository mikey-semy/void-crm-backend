"""
Роутер авторизации администраторов.

Предоставляет отдельные endpoints для аутентификации администраторов:
- POST /admin/auth - Вход в систему (только для роли admin)
- POST /admin/auth/refresh - Обновление токенов
- POST /admin/auth/logout - Выход из системы

Отличие от /api/v1/auth: проверяется наличие роли "admin" у пользователя.
"""

from fastapi import Cookie, Depends, Header, Query, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.dependencies import AuthServiceDep
from app.core.exceptions import ForbiddenError
from app.routers.base import BaseRouter
from app.schemas.v1.auth import LogoutResponseSchema, TokenResponseSchema


class AdminAuthRouter(BaseRouter):
    """
    Роутер авторизации для администраторов.

    Использует существующий AuthService, но добавляет проверку роли admin.
    Frontend вызывает /admin/auth вместо /auth для входа в админ-панель.
    """

    def __init__(self):
        """Инициализация роутера с пустым префиксом (auth добавляется через prefix)."""
        super().__init__(prefix="auth", tags=["Admin - Authentication"])

    def configure(self):
        """Настройка endpoints роутера."""

        # ==================== LOGIN ====================

        @self.router.post(
            path="",
            response_model=TokenResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""\
## 🔐 Вход администратора в систему

Аутентифицирует пользователя и проверяет, что у него есть роль "admin".
Возвращает JWT токены для доступа к админ-панели.

### Параметры:
- **username** — email, username или телефон администратора
- **password** — пароль администратора
- **use_cookies** — сохранить токены в cookies (по умолчанию True)

### Отличие от /auth/login:
- Проверяет наличие роли "admin" у пользователя
- При отсутствии роли возвращает 403 Forbidden

### Returns:
- **access_token** — JWT токен доступа
- **refresh_token** — refresh токен
- **token_type** — тип токена (Bearer)
- **expires_in** — время жизни access токена в секундах
""",
            responses={
                200: {"description": "Успешная аутентификация администратора"},
                401: {"description": "Неверные учетные данные"},
                403: {"description": "Пользователь не является администратором"},
                429: {"description": "Превышен лимит запросов"},
            },
        )
        async def admin_login(
            response: Response,
            form_data: OAuth2PasswordRequestForm = Depends(),
            use_cookies: bool = Query(
                True, description="Использовать cookies для хранения токенов"
            ),
            auth_service: AuthServiceDep = None,
        ) -> TokenResponseSchema:
            """
            Аутентификация администратора с проверкой роли.

            Args:
                response: Ответ FastAPI для установки cookies.
                form_data: Данные формы аутентификации (email, password).
                use_cookies: Использовать ли cookies для хранения токенов.
                auth_service: Сервис аутентификации (dependency injection).

            Returns:
                TokenResponseSchema: Токены доступа.

            Raises:
                InvalidCredentialsError: Неверные учетные данные.
                ForbiddenError: Пользователь не является администратором.
            """
            # 1. Аутентифицируем пользователя через существующий сервис
            # Сначала получим данные пользователя для проверки роли
            from app.repository.v1.users import UserRepository

            user_repo = UserRepository(session=auth_service.repository.session)
            user = await user_repo.get_user_by_identifier(form_data.username)

            if not user:
                from app.core.exceptions import InvalidCredentialsError

                raise InvalidCredentialsError()

            # 2. Проверяем роль ПЕРЕД аутентификацией (чтобы не тратить ресурсы)
            if user.role != "admin":
                raise ForbiddenError(
                    detail="Доступ только для администраторов. "
                    "Используйте /auth/login для входа как обычный пользователь."
                )

            # 3. Выполняем полную аутентификацию (проверка пароля, генерация токенов)
            return await auth_service.authenticate(
                form_data=form_data, response=response, use_cookies=use_cookies
            )

        # ==================== REFRESH TOKEN ====================

        @self.router.post(
            path="/refresh",
            response_model=TokenResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""\
## 🔄 Обновление токена администратора

Получение нового access токена с помощью refresh токена.

### Источники refresh токена:
- **refresh-token** (заголовок) — приоритетный источник
- **refresh_token** (cookie) — используется если заголовок отсутствует

### Returns:
- **access_token** — новый JWT токен доступа
- **refresh_token** — новый refresh токен (ротация)
- **token_type** — тип токена (Bearer)
- **expires_in** — время жизни нового access токена
""",
            responses={
                200: {"description": "Токен успешно обновлен"},
                401: {"description": "Refresh токен отсутствует"},
                419: {"description": "Refresh токен просрочен"},
                422: {"description": "Невалидный refresh токен"},
            },
        )
        async def admin_refresh_token(
            response: Response,
            use_cookies: bool = Query(
                True, description="Использовать cookies для токенов"
            ),
            refresh_token_header: str | None = Header(
                None, alias="refresh-token", description="Refresh токен из заголовка"
            ),
            refresh_token_cookie: str | None = Cookie(
                None, alias="refresh_token", description="Refresh токен из cookie"
            ),
            auth_service: AuthServiceDep = None,
        ) -> TokenResponseSchema:
            """
            Обновление токена доступа администратора.

            Args:
                response: Ответ FastAPI для установки cookies.
                use_cookies: Использовать ли cookies для хранения токенов.
                refresh_token_header: Refresh токен из заголовка запроса.
                refresh_token_cookie: Refresh токен из cookie.
                auth_service: Сервис аутентификации (dependency injection).

            Returns:
                TokenResponseSchema: Обновленные токены.
            """
            # Приоритет: заголовок -> cookie
            refresh_token = refresh_token_header or refresh_token_cookie

            return await auth_service.refresh_token(
                refresh_token=refresh_token, response=response, use_cookies=use_cookies
            )

        # ==================== LOGOUT ====================

        @self.router.post(
            path="/logout",
            response_model=LogoutResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""\
## 🚪 Выход администратора из системы

Завершает сессию администратора и добавляет токены в черный список.

### Источники токена:
- **Authorization** (заголовок) — Bearer токен
- **access_token** (cookie) — токен из cookie

### Query Parameters:
- **clear_cookies** — очистить cookies при выходе (по умолчанию True)

### Returns:
- **success** — результат операции
- **message** — сообщение о выходе
- **data** — объект с полем logged_out_at
""",
            responses={
                200: {"description": "Успешный выход из системы"},
                401: {"description": "Токен отсутствует"},
                419: {"description": "Токен просрочен"},
                422: {"description": "Невалидный токен"},
            },
        )
        async def admin_logout(
            response: Response,
            clear_cookies: bool = Query(
                True, description="Очистить cookies при выходе"
            ),
            authorization: str | None = Header(
                None, description="Bearer токен доступа"
            ),
            access_token_cookie: str | None = Cookie(
                None, alias="access_token", description="Access токен из cookie"
            ),
            auth_service: AuthServiceDep = None,
        ) -> LogoutResponseSchema:
            """
            Выход администратора из системы.

            Args:
                response: Ответ FastAPI для очистки cookies.
                clear_cookies: Очистить ли cookies при выходе.
                authorization: Bearer токен из заголовка запроса.
                access_token_cookie: Access токен из cookie.
                auth_service: Сервис аутентификации (dependency injection).

            Returns:
                LogoutResponseSchema: Результат выхода с временной меткой.
            """
            # Приоритет: заголовок -> cookie
            if not authorization and access_token_cookie:
                authorization = f"Bearer {access_token_cookie}"

            return await auth_service.logout(
                authorization=authorization,
                response=response,
                clear_cookies=clear_cookies,
            )
