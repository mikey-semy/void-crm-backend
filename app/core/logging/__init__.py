"""
Модуль настройки логирования.

Содержит функцию setup_logging для централизованной настройки логирования приложения.
"""

import logging
import os
from pathlib import Path

from app.core.settings import settings

from .formatters import CustomJsonFormatter, PrettyFormatter


def setup_logging():
    """
    Настраивает систему логирования в приложении.

    - Очищает все старые обработчики root-логгера
    - Добавляет консольный обработчик с выбранным форматтером (pretty/json)
    - Добавляет файловый обработчик с JSON-форматтером
    - Создаёт директории для логов, если они отсутствуют
    - Устанавливает уровень логирования согласно настройкам
    """
    root = logging.getLogger()

    # Очищаем старые обработчики
    if root.handlers:
        for handler in root.handlers:
            root.removeHandler(handler)

    # Консольный хендлер с pretty/json форматом
    console_formatter = CustomJsonFormatter() if settings.logging.LOG_FORMAT == "json" else PrettyFormatter()
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    root.addHandler(console_handler)

    # Пути для логов
    primary_log_path = settings.logging.LOG_FILE
    fallback_log_path = "./logs/app.log"

    # Попытка использовать основной путь
    if primary_log_path:
        try:
            log_path = Path(primary_log_path)
            if not log_path.parent.exists():
                os.makedirs(str(log_path.parent), exist_ok=True)

            # Проверяем возможность записи
            with open(
                file=log_path,
                mode=settings.logging.FILE_MODE,
                encoding=settings.logging.ENCODING,
            ) as _:
                pass

            file_handler = logging.FileHandler(
                filename=log_path,
                mode=settings.logging.FILE_MODE,
                encoding=settings.logging.ENCODING,
            )
            file_handler.setFormatter(CustomJsonFormatter())
            root.addHandler(file_handler)
            print(f"✅ Логи будут писаться в: {log_path}")
        except (PermissionError, OSError) as e:
            print(f"⚠️ Не удалось использовать основной файл логов {primary_log_path}: {e}")
            primary_log_path = None

    # Если основной путь не удалось использовать, используем резервный
    if not primary_log_path:
        try:
            fallback_path = Path(fallback_log_path)
            if not fallback_path.parent.exists():
                os.makedirs(str(fallback_path.parent), exist_ok=True)

            file_handler = logging.FileHandler(
                filename=str(fallback_path),
                mode=settings.logging.FILE_MODE,
                encoding=settings.logging.ENCODING,
            )
            file_handler.setFormatter(CustomJsonFormatter())
            root.addHandler(file_handler)
            print(f"✅ Используем резервный путь для логов: {fallback_path}")
        except (PermissionError, OSError) as e:
            print(f"❌ Не удалось создать файл логов: {e}")

    # Устанавливаем уровень логирования
    root.setLevel(settings.logging.LOG_LEVEL)

    # Подавляем логи от некоторых библиотек
    for logger_name in [
        "python_multipart",
        "sqlalchemy.engine",
        "passlib",
        "httpx",
        "httpcore",
    ]:
        logging.getLogger(logger_name).setLevel(logging.WARNING)
