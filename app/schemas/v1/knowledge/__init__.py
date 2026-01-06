"""Схемы для базы знаний."""

from .base import (
    KnowledgeArticleBaseSchema,
    KnowledgeArticleDetailSchema,
    KnowledgeArticleListItemSchema,
    KnowledgeAuthorSchema,
    KnowledgeCategoryBaseSchema,
    KnowledgeCategoryListItemSchema,
    KnowledgeTagBaseSchema,
    KnowledgeTagListItemSchema,
)
from .requests import (
    KnowledgeArticleCreateSchema,
    KnowledgeArticleUpdateSchema,
    KnowledgeCategoryCreateSchema,
    KnowledgeCategoryUpdateSchema,
    KnowledgeSearchQuerySchema,
    KnowledgeTagCreateSchema,
    KnowledgeTagUpdateSchema,
)
from .responses import (
    KnowledgeArticleDeletedSchema,
    KnowledgeArticleListResponseSchema,
    KnowledgeArticleResponseSchema,
    KnowledgeCategoryDeletedSchema,
    KnowledgeCategoryListResponseSchema,
    KnowledgeCategoryResponseSchema,
    KnowledgeSearchResponseSchema,
    KnowledgeTagDeletedSchema,
    KnowledgeTagListResponseSchema,
    KnowledgeTagResponseSchema,
)

__all__ = [
    # Base
    "KnowledgeCategoryBaseSchema",
    "KnowledgeCategoryListItemSchema",
    "KnowledgeTagBaseSchema",
    "KnowledgeTagListItemSchema",
    "KnowledgeAuthorSchema",
    "KnowledgeArticleBaseSchema",
    "KnowledgeArticleListItemSchema",
    "KnowledgeArticleDetailSchema",
    # Requests
    "KnowledgeCategoryCreateSchema",
    "KnowledgeCategoryUpdateSchema",
    "KnowledgeTagCreateSchema",
    "KnowledgeTagUpdateSchema",
    "KnowledgeArticleCreateSchema",
    "KnowledgeArticleUpdateSchema",
    "KnowledgeSearchQuerySchema",
    # Responses
    "KnowledgeCategoryResponseSchema",
    "KnowledgeCategoryListResponseSchema",
    "KnowledgeTagResponseSchema",
    "KnowledgeTagListResponseSchema",
    "KnowledgeArticleResponseSchema",
    "KnowledgeArticleListResponseSchema",
    "KnowledgeSearchResponseSchema",
    "KnowledgeArticleDeletedSchema",
    "KnowledgeCategoryDeletedSchema",
    "KnowledgeTagDeletedSchema",
]
