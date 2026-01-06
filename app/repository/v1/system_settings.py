"""Репозиторий для работы с системными настройками."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.v1 import SystemSettingsModel
from app.repository.base import BaseRepository


class SystemSettingsRepository(BaseRepository[SystemSettingsModel]):
    """
    Репозиторий для работы с системными настройками.

    Предоставляет методы для работы с key-value настройками системы.
    Использует базовые методы BaseRepository согласно документации.
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализирует репозиторий.

        Args:
            session: Асинхронная сессия SQLAlchemy
        """
        super().__init__(session, SystemSettingsModel)

    async def get_by_prefix(self, prefix: str) -> list[SystemSettingsModel]:
        """
        Получает все настройки с указанным префиксом.

        Args:
            prefix: Префикс ключа (например, "rag.")

        Returns:
            Список настроек
        """
        return await self.filter_by(key__like=f"{prefix}%")

    async def set_value(
        self,
        key: str,
        value: str,
        description: str | None = None,
    ) -> SystemSettingsModel:
        """
        Устанавливает значение настройки (создаёт или обновляет).

        Использует update_or_create из BaseRepository.

        Args:
            key: Ключ настройки
            value: Значение
            description: Описание (опционально)

        Returns:
            SystemSettingsModel
        """
        defaults = {"value": value}
        if description is not None:
            defaults["description"] = description

        setting, _ = await self.update_or_create(
            filters={"key": key},
            defaults=defaults,
        )
        return setting

    async def get_value(self, key: str, default: str = "") -> str:
        """
        Получает значение настройки.

        Args:
            key: Ключ настройки
            default: Значение по умолчанию

        Returns:
            Значение настройки или default
        """
        setting = await self.get_item_by_field("key", key)
        return setting.value if setting else default

    async def delete_by_key(self, key: str) -> bool:
        """
        Удаляет настройку по ключу.

        Args:
            key: Ключ настройки

        Returns:
            True если удалено, False если не найдено
        """
        count = await self.delete_by_filters(key=key)
        return count > 0
