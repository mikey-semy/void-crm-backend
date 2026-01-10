"""Схемы для MCP API базы знаний."""

from .base import (
    MCPArticleContentSchema,
    MCPArticleSnippetSchema,
    MCPCategoryItemSchema,
    MCPIndexDataSchema,
    MCPSnippetItemSchema,
    MCPSuccessDataSchema,
    MCPTagItemSchema,
)
from .requests import (
    MCPCreateArticleRequestSchema,
    MCPSearchRequestSchema,
    MCPUpdateArticleRequestSchema,
)
from .responses import (
    MCPArticleResponseSchema,
    MCPCategoriesResponseSchema,
    MCPIndexResponseSchema,
    MCPSearchResponseSchema,
    MCPSnippetsResponseSchema,
    MCPSuccessResponseSchema,
    MCPTagsResponseSchema,
)

__all__ = [
    # Base
    "MCPArticleSnippetSchema",
    "MCPArticleContentSchema",
    "MCPCategoryItemSchema",
    "MCPTagItemSchema",
    "MCPSnippetItemSchema",
    "MCPSuccessDataSchema",
    "MCPIndexDataSchema",
    # Requests
    "MCPSearchRequestSchema",
    "MCPCreateArticleRequestSchema",
    "MCPUpdateArticleRequestSchema",
    # Responses
    "MCPSearchResponseSchema",
    "MCPArticleResponseSchema",
    "MCPCategoriesResponseSchema",
    "MCPTagsResponseSchema",
    "MCPSnippetsResponseSchema",
    "MCPSuccessResponseSchema",
    "MCPIndexResponseSchema",
]