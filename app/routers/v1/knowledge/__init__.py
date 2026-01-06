"""
Роутеры для базы знаний.

Содержит роутеры для:
- Статей (articles) — публичные и защищённые endpoints
- Категорий (categories) — публичные и защищённые endpoints
- Тегов (tags) — публичные и защищённые endpoints
- Поиска (search) — полнотекстовый поиск
- MCP (mcp) — API для интеграции с Claude Code
"""

from .articles import KnowledgeArticleProtectedRouter, KnowledgeArticleRouter
from .categories import KnowledgeCategoryProtectedRouter, KnowledgeCategoryRouter
from .mcp import KnowledgeMCPRouter
from .search import KnowledgeSearchRouter
from .tags import KnowledgeTagProtectedRouter, KnowledgeTagRouter

__all__ = [
    # Articles
    "KnowledgeArticleRouter",
    "KnowledgeArticleProtectedRouter",
    # Categories
    "KnowledgeCategoryRouter",
    "KnowledgeCategoryProtectedRouter",
    # Tags
    "KnowledgeTagRouter",
    "KnowledgeTagProtectedRouter",
    # Search
    "KnowledgeSearchRouter",
    # MCP
    "KnowledgeMCPRouter",
]
