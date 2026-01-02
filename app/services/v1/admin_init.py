"""
Сервис инициализации администраторов.

Автоматически создаёт администраторов при первом запуске приложения,
используя данные из переменных окружения:
- DEFAULT_ADMIN_* - дефолтный администратор
- ADMINS - дополнительные администраторы (username:email:phone:password,...)
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import PasswordManager
from app.models.v1.roles import RoleCode, UserRoleModel
from app.repository.v1.users import UserRepository
from app.services.base import BaseService


class AdminInitService(BaseService):
    """
    Сервис инициализации администраторов.

    Создаёт админов из ENV переменных при первом запуске.
    Использует UserRepository для работы с базой данных.
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализация сервиса.

        Args:
            session: Асинхронная сессия базы данных.
        """
        super().__init__(session=session)
        self.user_repository = UserRepository(session=session)
        self.password_manager = PasswordManager()

    async def create_default_admin_if_not_exists(self) -> None:
        """
        Создаёт всех администраторов из ENV, если они не существуют.

        Процесс:
        1. Создаёт дефолтного админа из DEFAULT_ADMIN_* переменных
        2. Создаёт дополнительных админов из ADMINS переменной

        Raises:
            Exception: Любые исключения логируются и пробрасываются дальше.
        """
        # 1. Создаём дефолтного админа
        await self._create_admin(
            username=self.settings.DEFAULT_ADMIN_USERNAME,
            email=self.settings.DEFAULT_ADMIN_EMAIL,
            phone=self.settings.DEFAULT_ADMIN_PHONE,
            password=self.settings.DEFAULT_ADMIN_PASSWORD.get_secret_value(),
            full_name=None,  # Пользователь заполнит сам в профиле
        )

        # 2. Создаём дополнительных админов из ADMINS
        additional_admins = self.settings.additional_admins
        for admin_data in additional_admins:
            await self._create_admin(
                username=admin_data["username"],
                email=admin_data["email"],
                phone=admin_data["phone"],
                password=admin_data["password"],
                full_name=None,  # Пользователь заполнит сам в профиле
            )

    async def _create_admin(
        self,
        username: str,
        email: str,
        phone: str,
        password: str,
        full_name: str,
    ) -> None:
        """
        Создаёт администратора с ролью admin.

        Args:
            username: Имя пользователя.
            email: Email администратора.
            phone: Телефон администратора.
            password: Пароль (будет захеширован).
            full_name: Полное имя.
        """
        try:
            # Проверяем существование по username или email
            existing_admin = await self.user_repository.get_item_by_field(
                "username", username
            )
            if not existing_admin:
                existing_admin = await self.user_repository.get_item_by_field(
                    "email", email
                )

            if existing_admin:
                self.logger.info(
                    "✅ Админ '%s' уже существует - проверяем актуальность данных",
                    username,
                )
                # Проверяем, есть ли у него роль admin
                await self._ensure_admin_role(existing_admin.id)
                # Синхронизируем данные из ENV (email, phone, password)
                await self._sync_admin_data(
                    existing_admin, email=email, phone=phone, full_name=full_name, password=password
                )
                return

            # Хешируем пароль
            hashed_password = self.password_manager.hash_password(password)

            # Создаём словарь для создания пользователя
            admin_data = {
                "username": username,
                "email": email,
                "phone": phone,
                "password_hash": hashed_password,
                "is_active": True,
                "email_verified": True,  # Админ сразу верифицирован
                "full_name": full_name,
            }

            # Создаём админа через repository
            new_user = await self.user_repository.create_item(admin_data)

            self.logger.info(
                "✅ Создан админ: username='%s', email='%s', phone='%s'",
                username,
                email,
                phone,
            )

            # Назначаем роль admin
            await self._assign_admin_role(new_user.id)

        except Exception as e:
            self.logger.error(
                "❌ Ошибка создания администратора '%s': %s",
                username,
                e,
                exc_info=True,
            )
            raise

    async def _assign_admin_role(self, user_id) -> None:
        """
        Назначает роль admin пользователю.

        Args:
            user_id: UUID пользователя.
        """
        try:
            # Создаём запись в user_role_assignments
            role_assignment = UserRoleModel(
                user_id=user_id,
                role_code=RoleCode.ADMIN,
            )
            self.session.add(role_assignment)
            await self.session.commit()

            self.logger.info(
                "✅ Назначена роль 'admin' для пользователя: %s",
                user_id,
            )
        except Exception as e:
            self.logger.error(
                "❌ Ошибка назначения роли admin для %s: %s",
                user_id,
                e,
                exc_info=True,
            )
            await self.session.rollback()
            raise

    async def _sync_admin_data(
        self,
        admin,
        email: str,
        phone: str,
        full_name: str,
        password: str,
    ) -> None:
        """
        Синхронизирует данные админа с ENV.

        Обновляет email, phone, full_name и password если они изменились.

        Args:
            admin: Существующий пользователь-админ.
            email: Email из ENV.
            phone: Телефон из ENV.
            full_name: Полное имя.
            password: Пароль из ENV (сверяется с хешем).
        """
        update_data = {}

        if admin.email != email:
            update_data["email"] = email
            self.logger.info(
                "📧 Email админа '%s' изменён: %s → %s",
                admin.username,
                admin.email,
                email,
            )

        if admin.phone != phone:
            update_data["phone"] = phone
            self.logger.info(
                "📱 Телефон админа '%s' изменён: %s → %s",
                admin.username,
                admin.phone,
                phone,
            )

        # Обновляем full_name только если в ENV указано конкретное значение
        # Если full_name=None в ENV, не трогаем существующее значение в БД
        if full_name is not None and admin.full_name != full_name:
            update_data["full_name"] = full_name
            self.logger.info(
                "👤 full_name админа '%s' изменён: '%s' → '%s'",
                admin.username,
                admin.full_name,
                full_name,
            )

        # Проверяем, изменился ли пароль
        if not self.password_manager.verify(admin.password_hash, password):
            update_data["password_hash"] = self.password_manager.hash_password(password)
            self.logger.info(
                "🔑 Пароль админа '%s' обновлён из ENV",
                admin.username,
            )

        if update_data:
            await self.user_repository.update_item(admin.id, update_data)
            self.logger.info(
                "✅ Данные админа '%s' синхронизированы с ENV",
                admin.username,
            )

    async def _ensure_admin_role(self, user_id) -> None:
        """
        Проверяет и добавляет роль admin, если её нет.

        Args:
            user_id: UUID пользователя.
        """
        from sqlalchemy import select

        # Проверяем наличие роли admin
        stmt = select(UserRoleModel).where(
            UserRoleModel.user_id == user_id,
            UserRoleModel.role_code == RoleCode.ADMIN,
        )
        result = await self.session.execute(stmt)
        existing_role = result.scalar_one_or_none()

        if not existing_role:
            self.logger.info(
                "⚠️ У пользователя %s нет роли admin - добавляем",
                user_id,
            )
            await self._assign_admin_role(user_id)
        else:
            self.logger.debug(
                "✅ У пользователя %s уже есть роль admin",
                user_id,
            )
