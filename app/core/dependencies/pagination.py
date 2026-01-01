"""
Зависимости для пагинации.
"""

from typing import Annotated

from fastapi import Depends

from app.schemas.pagination import PaginationParamsSchema


def get_pagination_params(
    pagination: PaginationParamsSchema = Depends(),
) -> PaginationParamsSchema:
    """
    Зависимость для получения параметров пагинации.

    Args:
        pagination: Параметры пагинации из query string.

    Returns:
        PaginationParamsSchema: Параметры пагинации.
    """
    return pagination


# Типизированная зависимость
PaginationDep = Annotated[PaginationParamsSchema, Depends(get_pagination_params)]
