import logging
from typing import TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import settings
from app.models import BaseModel
from app.schemas import BaseSchema

M = TypeVar("M", bound=BaseModel)
T = TypeVar("T", bound=BaseSchema)


class SessionMixin:
    """
    Миксин для предоставления экземпляра сессии базы данных.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Инициализирует SessionMixin.

        Args:
            session (AsyncSession): Асинхронная сессия базы данных.
        """
        self.session = session


class BaseService(SessionMixin):
    """
    Базовый класс для сервисов приложения.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.settings = settings
