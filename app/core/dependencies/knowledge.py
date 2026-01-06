"""Зависимости для работы с базой знаний."""

from typing import Annotated

from fastapi import Depends

from app.core.dependencies.database import AsyncSessionDep
from app.services.v1.knowledge import KnowledgeService


async def get_knowledge_service(session: AsyncSessionDep) -> KnowledgeService:
    """
    Зависимость для получения сервиса базы знаний.

    Args:
        session: Асинхронная сессия базы данных

    Returns:
        KnowledgeService: Экземпляр сервиса базы знаний

    Usage:
        ```python
        @router.get("/knowledge/articles")
        async def get_articles(service: KnowledgeServiceDep):
            return await service.get_published_articles(pagination)
        ```
    """
    return KnowledgeService(session)


# Типизированная зависимость
KnowledgeServiceDep = Annotated[KnowledgeService, Depends(get_knowledge_service)]
