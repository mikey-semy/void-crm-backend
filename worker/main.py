"""
Void CRM Worker - точка входа.

Универсальный воркер для обработки задач из RabbitMQ.

Использует FastStream для:
- Автоматического управления подключениями
- AsyncAPI документации
- Retry логики
- Мониторинга

Запуск:
    python -m worker.main

Или через FastStream CLI:
    faststream run worker.main:app
"""

import logging

from faststream import FastStream

from worker.broker import broker, router

# Импортируем обработчики чтобы они зарегистрировались
from worker import handlers  # noqa: F401

logger = logging.getLogger(__name__)

# Подключаем роутер к брокеру
broker.include_router(router)

# Создаём приложение FastStream
app = FastStream(broker)


@app.on_startup
async def on_startup() -> None:
    """Инициализация при запуске воркера."""
    logger.info("🚀 Void CRM Worker запущен")
    logger.info("📋 Очереди:")
    logger.info("   - knowledge_article_indexing (индексация статей)")


@app.on_shutdown
async def on_shutdown() -> None:
    """Очистка при остановке воркера."""
    logger.info("🛑 Void CRM Worker остановлен")


def main() -> None:
    """Точка входа для запуска воркера."""
    import asyncio

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Отключаем DEBUG логи от aiormq (heartbeat спам)
    logging.getLogger("aiormq").setLevel(logging.WARNING)
    logging.getLogger("aio_pika").setLevel(logging.WARNING)

    try:
        asyncio.run(app.run())
    except KeyboardInterrupt:
        logger.info("🛑 Остановка воркера по Ctrl+C")


if __name__ == "__main__":
    main()
