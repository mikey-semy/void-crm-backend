"""Схемы ответов для базы знаний."""

from pydantic import Field

from app.schemas import BaseResponseSchema, PaginatedDataSchema, PaginatedResponseSchema

from .base import (
    KnowledgeArticleDetailSchema,
    KnowledgeArticleListItemSchema,
    KnowledgeCategoryListItemSchema,
    KnowledgeTagListItemSchema,
)


# ==================== КАТЕГОРИИ ====================


class KnowledgeCategoryResponseSchema(BaseResponseSchema):
    """Ответ с одной категорией."""

    data: KnowledgeCategoryListItemSchema = Field(description="Данные категории")


class KnowledgeCategoryListResponseSchema(BaseResponseSchema):
    """Ответ со списком категорий."""

    data: list[KnowledgeCategoryListItemSchema] = Field(description="Список категорий")


# ==================== ТЕГИ ====================


class KnowledgeTagResponseSchema(BaseResponseSchema):
    """Ответ с одним тегом."""

    data: KnowledgeTagListItemSchema = Field(description="Данные тега")


class KnowledgeTagListResponseSchema(BaseResponseSchema):
    """Ответ со списком тегов."""

    data: list[KnowledgeTagListItemSchema] = Field(description="Список тегов")


# ==================== СТАТЬИ ====================


class KnowledgeArticleResponseSchema(BaseResponseSchema):
    """Ответ с детальной информацией о статье."""

    data: KnowledgeArticleDetailSchema = Field(description="Данные статьи")


class KnowledgeArticleListResponseSchema(PaginatedResponseSchema):
    """Ответ со списком статей с пагинацией."""

    data: PaginatedDataSchema[KnowledgeArticleListItemSchema] = Field(description="Список статей с пагинацией")


# ==================== ПОИСК ====================


class KnowledgeSearchResponseSchema(PaginatedResponseSchema):
    """Ответ с результатами поиска."""

    data: PaginatedDataSchema[KnowledgeArticleListItemSchema] = Field(description="Результаты поиска с пагинацией")


# ==================== ОПЕРАЦИИ ====================


class KnowledgeArticleDeletedSchema(BaseResponseSchema):
    """Ответ об удалении статьи."""

    message: str = Field(default="Статья успешно удалена", description="Сообщение")


class KnowledgeCategoryDeletedSchema(BaseResponseSchema):
    """Ответ об удалении категории."""

    message: str = Field(default="Категория успешно удалена", description="Сообщение")


class KnowledgeTagDeletedSchema(BaseResponseSchema):
    """Ответ об удалении тега."""

    message: str = Field(default="Тег успешно удалён", description="Сообщение")


# ==================== AI ====================


class KnowledgeGeneratedDescriptionSchema(BaseResponseSchema):
    """Ответ с сгенерированным описанием."""

    data: str = Field(description="Сгенерированное описание")
