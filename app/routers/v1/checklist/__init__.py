"""Роутеры для чек-листа партнёрства."""

from .categories import ChecklistCategoryRouter
from .statistics import ChecklistStatisticsRouter
from .tasks import ChecklistCategoryTaskRouter, ChecklistTaskRouter
from .websocket import ChecklistWebSocketRouter

__all__ = [
    "ChecklistCategoryRouter",
    "ChecklistTaskRouter",
    "ChecklistCategoryTaskRouter",
    "ChecklistStatisticsRouter",
    "ChecklistWebSocketRouter",
]
