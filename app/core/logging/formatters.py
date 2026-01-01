"""
Модуль форматтеров для логирования.

Содержит классы для форматирования логов в различных стилях:

PrettyFormatter: форматирует логи с цветами и эмодзи для удобного чтения в консоли
CustomJsonFormatter: форматирует логи в JSON формате для машинной обработки
"""

import json
import logging
from datetime import datetime

from app.core.settings import settings


class PrettyFormatter(logging.Formatter):
    """
    Добавляет цветовое оформление в зависимости от уровня логирования,
    а также соответствующие эмодзи.

    Attributes:
        COLORS: Словарь с ANSI-кодами цветов для разных уровней логирования
        EMOJIS: Словарь с эмодзи для разных уровней логирования
        RESET: ANSI-код для сброса форматирования
    """

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[41m",  # Red background
    }
    EMOJIS = {
        "DEBUG": "🔍",
        "INFO": "✨",
        "WARNING": "⚠️",
        "ERROR": "❌",
        "CRITICAL": "💥",
    }

    RESET = "\033[0m"

    def format(self, record):
        """
        Форматирует запись лога с цветами и эмодзи.

        Args:
            record: Запись лога для форматирования

        Returns:
            str: Отформатированная строка лога
        """
        standard_attrs = {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "message",
            "asctime",
            "taskName",
        }

        extra_attrs = {k: v for k, v in vars(record).items() if k not in standard_attrs}

        if extra_attrs:
            extra_msg = f"\033[33m[extra: {extra_attrs}]\033[0m"
        else:
            extra_msg = ""

        emoji = self.EMOJIS.get(record.levelname, "")

        base_msg = settings.logging.PRETTY_FORMAT % {
            "asctime": self.formatTime(record),
            "name": record.name,
            "levelname": f"{self.COLORS.get(record.levelname, '')}{record.levelname} {self.RESET}",
            "message": f"{emoji} {record.getMessage()}",
        }

        return f"{base_msg} {extra_msg}" if extra_msg else base_msg


class CustomJsonFormatter(logging.Formatter):
    """
    Форматтер для вывода логов в JSON формате.

    Преобразует записи логов в структурированный JSON формат,
    используя шаблон из настроек.
    """

    def format(self, record):
        """
        Форматирует запись лога в JSON формате.

        Args:
            record: Запись лога для форматирования

        Returns:
            str: Отформатированная строка лога в JSON формате
        """
        log_data = settings.logging.JSON_FORMAT.copy()

        for key, value in log_data.items():
            if key == "timestamp":
                dt = datetime.fromtimestamp(record.created)
                log_data[key] = dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            else:
                log_data[key] = value % {
                    "asctime": self.formatTime(record),
                    "levelname": record.levelname,
                    "module": record.module,
                    "funcName": record.funcName,
                    "message": record.getMessage(),
                }

        # Добавляем traceback если есть exc_info
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Добавляем stack_info если есть
        if record.stack_info:
            log_data["stack_info"] = self.formatStack(record.stack_info)

        return json.dumps(log_data, ensure_ascii=False)
