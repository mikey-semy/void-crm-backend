"""
Модуль инициализации и завершения работы с базами данных для FastAPI-приложения.

Назначение:
- Автоматически инициализирует подключение к PostgreSQL при запуске приложения.
- Корректно закрывает подключения к обеим базам данных при завершении работы приложения.
- Сохраняет экземпляры клиентов в app.state для централизованного доступа из любого места приложения.

Используемые механизмы:
- Декораторы register_startup_handler и register_shutdown_handler регистрируют функции для событий старта и остановки FastAPI.
- Подключения к базам данных создаются один раз на старте и закрываются при завершении, что предотвращает утечки ресурсов.

Экспортируемые функции:
- initialize_databases: Инициализация обеих баз данных при старте приложения.
- close_database_connections: Корректное закрытие подключений при остановке приложения.
"""

from fastapi import FastAPI

from app.core.connections.database import DatabaseClient
from app.core.lifespan.base import register_shutdown_handler, register_startup_handler


@register_startup_handler
async def initialize_database(app: FastAPI):
    """
    Инициализация обеих баз данных при старте приложения.

    Подключает PostgreSQL, сохраняет клиентов в app.state для дальнейшего использования.
    """
    client = DatabaseClient()
    await client.connect()
    app.state.pg_client = client


@register_shutdown_handler
async def close_database_connection(app: FastAPI):
    """
    Закрытие подключений к базам данных при остановке приложения.

    Безопасно закрывает подключения к PostgreSQL, если они были инициализированы.
    """
    if hasattr(app.state, "pg_client"):
        await app.state.pg_client.close()
