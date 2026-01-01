"""Схемы для пагинации и поиска."""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

from app.schemas.base import BaseResponseSchema, CommonBaseSchema

T = TypeVar("T")


class SortOption(BaseModel):
    """
    Базовый класс для опций сортировки.

    Attributes:
        field (str): Идентификатор поля для использования в запросах сортировки.
        description (str): Человекочитаемое описание поля сортировки.
    """

    field: str
    description: str


class BaseSortFields:
    """
    Базовый класс для полей сортировки.

    Определяет стандартные поля сортировки (created_at, updated_at).
    """

    CREATED_AT = SortOption(field="created_at", description="Сортировка по дате создания")
    UPDATED_AT = SortOption(field="updated_at", description="Сортировка по дате обновления")

    @classmethod
    def get_default(cls) -> SortOption:
        """Возвращает поле сортировки по умолчанию (UPDATED_AT)."""
        return cls.UPDATED_AT

    @classmethod
    def get_all_fields(cls) -> dict[str, SortOption]:
        """Возвращает все доступные поля сортировки."""
        fields = {}
        for base_cls in cls.__mro__:
            if hasattr(base_cls, "__dict__"):
                for name, value in base_cls.__dict__.items():
                    if isinstance(value, SortOption) and not name.startswith("_"):
                        fields[name] = value
        return fields

    @classmethod
    def get_field_values(cls) -> list[str]:
        """Возвращает список идентификаторов полей."""
        return [option.field for option in cls.get_all_fields().values()]

    @classmethod
    def is_valid_field(cls, field: str) -> bool:
        """Проверяет, является ли поле допустимым."""
        return field in cls.get_field_values()

    @classmethod
    def get_field_or_default(cls, field: str) -> str:
        """Возвращает поле или значение по умолчанию."""
        if cls.is_valid_field(field):
            return field
        return cls.get_default().field


class SortFields(BaseSortFields):
    """Стандартные поля сортировки."""

    pass


class SortFieldRegistry:
    """
    Реестр классов полей сортировки.
    """

    _registry: dict[str, type[BaseSortFields]] = {
        "default": SortFields,
    }

    @classmethod
    def register(cls, name: str, sort_class: type[BaseSortFields]):
        """Регистрирует класс сортировки для сущности."""
        cls._registry[name] = sort_class

    @classmethod
    def get_sort_field_class(cls, entity_name: str) -> type[BaseSortFields]:
        """Получает класс полей сортировки для сущности."""
        return cls._registry.get(entity_name, cls._registry["default"])


class PaginationParamsSchema(CommonBaseSchema):
    """
    Параметры пагинации и сортировки.

    Attributes:
        page (int): Номер страницы (начиная с 1).
        page_size (int): Количество элементов на странице (1-5000).
        sort_by (str): Поле для сортировки.
        sort_desc (bool): Флаг сортировки по убыванию.
    """

    page: int = Field(1, ge=1, description="Номер страницы (начиная с 1)")
    page_size: int = Field(20, ge=1, le=5000, description="Количество элементов на странице")
    sort_by: str = Field("created_at", description="Поле сортировки")
    sort_desc: bool = Field(True, description="Сортировка по убыванию")


class SearchParamsSchema(CommonBaseSchema):
    """
    Параметры поиска.

    Attributes:
        query (Optional[str]): Поисковый запрос.
        folder (Optional[str]): Фильтр по папке.
    """

    query: str | None = Field(None, description="Поисковый запрос")
    folder: str | None = Field(None, description="Фильтр по папке")


class PaginationMetaSchema(CommonBaseSchema):
    """
    Метаданные пагинации.

    Attributes:
        total (int): Общее количество элементов.
        page (int): Текущая страница.
        page_size (int): Размер страницы.
        total_pages (int): Общее количество страниц.
        has_next (bool): Есть ли следующая страница.
        has_prev (bool): Есть ли предыдущая страница.
    """

    total: int = Field(description="Общее количество элементов")
    page: int = Field(description="Текущая страница")
    page_size: int = Field(description="Размер страницы")
    total_pages: int = Field(description="Общее количество страниц")
    has_next: bool = Field(description="Есть ли следующая страница")
    has_prev: bool = Field(description="Есть ли предыдущая страница")


class PaginatedDataSchema(CommonBaseSchema, Generic[T]):
    """
    Данные с пагинацией.

    Attributes:
        items (List[T]): Список элементов.
        pagination (PaginationMetaSchema): Метаданные пагинации.
    """

    items: list[T] = Field(default_factory=list, description="Список элементов")
    pagination: PaginationMetaSchema = Field(description="Метаданные пагинации")


class PaginatedResponseSchema(BaseResponseSchema, Generic[T]):
    """
    Схема ответа с пагинацией.
    """

    data: PaginatedDataSchema[T] = Field(description="Данные с пагинацией")
