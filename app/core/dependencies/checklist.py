"""Зависимости для работы с чек-листом."""

from typing import Annotated

from fastapi import Depends

from app.core.dependencies.database import AsyncSessionDep
from app.services.v1.checklist import ChecklistService


async def get_checklist_service(session: AsyncSessionDep) -> ChecklistService:
    """
    Зависимость для получения сервиса чек-листа.

    Args:
        session: Асинхронная сессия базы данных

    Returns:
        ChecklistService: Экземпляр сервиса чек-листа

    Usage:
        ```python
        @router.get("/checklist")
        async def get_checklist(service: ChecklistServiceDep):
            return await service.get_all_categories_with_tasks()
        ```
    """
    return ChecklistService(session)


# Типизированная зависимость
ChecklistServiceDep = Annotated[ChecklistService, Depends(get_checklist_service)]
