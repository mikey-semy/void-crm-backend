"""
Модуль загрузки фикстур чек-листа при старте приложения.

Автоматически загружает начальные данные чек-листа партнёрства из JSON файла
при запуске приложения (если LOAD_FIXTURES=true).

Функции:
- load_fixtures_on_startup: Регистрируется как startup handler и вызывает все загрузчики фикстур
- load_checklist_fixtures: Загружает категории и задачи чек-листа из JSON файла
"""

import json
import logging

from fastapi import FastAPI

from app.core.connections.database import DatabaseClient
from app.core.lifespan.base import register_startup_handler
from app.core.settings import settings
from app.core.settings.paths import PathSettings
from app.services.v1.checklist import ChecklistService

logger = logging.getLogger("app.core.lifespan.fixtures")

# Путь к файлу с фикстурами
CHECKLIST_FILE = PathSettings.FIXTURES_DIR / "checklist.json"


@register_startup_handler
async def load_fixtures_on_startup(_app: FastAPI) -> None:
    """
    Загрузка фикстур при старте приложения.

    Проверяет флаг LOAD_FIXTURES и загружает начальные данные из JSON файлов.

    Args:
        _app: Экземпляр FastAPI приложения (не используется).
    """
    if not settings.LOAD_FIXTURES:
        logger.debug("Загрузка фикстур отключена в настройках (LOAD_FIXTURES=false)")
        return

    logger.info("Начало загрузки фикстур при запуске приложения")

    try:
        # Загрузка фикстур чек-листа
        await load_checklist_fixtures()
        logger.info("✅ Загрузка фикстур завершена успешно")
    except Exception as e:
        logger.error("❌ Ошибка при загрузке фикстур: %s", e, exc_info=True)
        # Не поднимаем исключение, чтобы не сломать запуск приложения


async def load_checklist_fixtures():
    """
    Загружает начальные данные чек-листа из JSON файла в базу данных.

    Создаёт категории и задачи из data/fixtures/checklist.json.
    НЕ загружает данные если в БД уже есть категории (чтобы сохранить изменения пользователя).
    """
    if not CHECKLIST_FILE.exists():
        logger.warning("Файл фикстур чек-листа не найден: %s", CHECKLIST_FILE)
        return

    # Загружаем JSON
    with open(CHECKLIST_FILE, encoding="utf-8") as f:
        checklist_data = json.load(f)

    logger.info("Загружено %d категорий из %s", len(checklist_data), CHECKLIST_FILE.name)

    db_client = DatabaseClient()
    session_factory = await db_client.connect()

    async with session_factory() as session:
        service = ChecklistService(session)

        # Проверяем, есть ли уже данные в БД
        existing_categories = await service.get_all_categories_with_tasks()
        if existing_categories:
            logger.info(
                "В БД уже есть %d категорий, пропускаем загрузку фикстур (чтобы сохранить изменения пользователя)",
                len(existing_categories),
            )
            return

        logger.info("Категорий нет в БД, загружаем из фикстур")

        # Словарь для маппинга string ID -> UUID
        category_id_map = {}

        # Статистика
        stats = {"categories": 0, "tasks": 0}

        # Создание категорий и задач
        for category_data in checklist_data:
            # Сохраняем string ID из фронтенда
            frontend_id = category_data["id"]

            # Подготовка данных категории (без tasks и id)
            cat_dict = {
                "title": category_data["title"],
                "description": category_data.get("description"),
                "icon": category_data.get("icon"),
                "color": category_data.get("color"),
                "order": category_data["order"],
            }

            # Создание категории
            category = await service.create_category(cat_dict)
            category_id_map[frontend_id] = category.id
            stats["categories"] += 1

            logger.debug(
                "Создана категория: %s (UUID=%s, frontend_id=%s)",
                category.title,
                category.id,
                frontend_id,
            )

            # Создание задач для этой категории
            for task_data in category_data.get("tasks", []):
                task_dict = {
                    "title": task_data["title"],
                    "description": task_data.get("description"),
                    "status": task_data.get("status", "pending"),
                    "priority": task_data.get("priority", "medium"),
                    "order": task_data["order"],
                    "category_id": category.id,  # Используем UUID категории
                }

                # Добавляем assignee только если он есть
                if "assignee" in task_data:
                    task_dict["assignee"] = task_data["assignee"]

                # Создание задачи
                task = await service.create_task(task_dict)
                stats["tasks"] += 1

                logger.debug(
                    "  Создана задача: %s (id=%s, priority=%s)",
                    task.title,
                    task.id,
                    task.priority,
                )

        # Коммит транзакции
        await session.commit()

        logger.info(
            "Загрузка данных завершена: создано категорий=%d, задач=%d",
            stats["categories"],
            stats["tasks"],
        )

        # Логируем маппинг frontend ID -> UUID (опционально)
        logger.debug("\nМаппинг frontend ID -> UUID:")
        for frontend_id, uuid in category_id_map.items():
            logger.debug("  %s -> %s", frontend_id, uuid)
