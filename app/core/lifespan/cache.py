"""
Модуль инициализации и завершения работы с Redis для FastAPI-приложения.

Назначение:
- Автоматически инициализирует подключение к Redis при запуске приложения.
- Корректно закрывает подключение к Redis при завершении работы приложения.
- Сохраняет экземпляр клиента Redis в app.state для централизованного доступа из любого места приложения.

Используемые механизмы:
- Декораторы register_startup_handler и register_shutdown_handler регистрируют функции для событий старта и остановки FastAPI.
- Подключение к Redis создаётся один раз на старте и закрывается при завершении, что предотвращает утечки ресурсов.

Экспортируемые функции:
- initialize_cache: Инициализация клиента Redis при старте приложения.
- close_cache_connection: Корректное закрытие подключения при остановке приложения.
"""

from fastapi import FastAPI

from app.core.connections.cache import RedisClient
from app.core.lifespan.base import register_shutdown_handler, register_startup_handler


@register_startup_handler
async def initialize_cache(app: FastAPI):
    """
    Инициализация клиента Redis при старте приложения.

    Flow:
        1. Создаёт экземпляр RedisClient.
        2. Устанавливает подключение к Redis.
        3. Сохраняет клиента в app.state для дальнейшего использования.

    Args:
        app (FastAPI): Экземпляр приложения FastAPI.

    Returns:
        None
    """
    client = RedisClient()
    await client.connect()
    app.state.redis_client = client


@register_shutdown_handler
async def close_cache_connection(app: FastAPI):
    """
    Закрытие подключения к Redis при остановке приложения.

    Flow:
        1. Проверяет, был ли инициализирован клиент Redis.
        2. Безопасно закрывает подключение к Redis.

    Args:
        app (FastAPI): Экземпляр приложения FastAPI.

    Returns:
        None
    """
    if hasattr(app.state, "redis_client"):
        await app.state.redis_client.close()
