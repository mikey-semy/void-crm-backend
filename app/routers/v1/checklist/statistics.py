"""
Роутер для статистики чек-листа.

Предоставляет endpoint для получения статистики по задачам.
"""

from app.core.dependencies.checklist import ChecklistServiceDep
from app.routers.base import ProtectedRouter


class ChecklistStatisticsRouter(ProtectedRouter):
    """
    Роутер для статистики чек-листа.

    Endpoints:
        GET /checklist/statistics - Получить статистику по задачам
    """

    def __init__(self):
        """Инициализирует ChecklistStatisticsRouter."""
        super().__init__(prefix="checklist", tags=["Checklist - Statistics"])

    def configure(self):
        """Настройка endpoint для статистики."""

        @self.router.get(
            path="/statistics",
            description="""\
## 📊 Получить статистику по задачам

Возвращает количество задач по каждому статусу.

### Returns:
- Статистика: {"pending": 15, "in_progress": 3, "completed": 8, "skipped": 1}
""",
        )
        async def get_statistics(
            service: ChecklistServiceDep,
        ) -> dict:
            """Получает статистику по задачам чек-листа."""
            stats = await service.get_statistics()

            return {"success": True, "message": "Статистика получена", "data": stats}
