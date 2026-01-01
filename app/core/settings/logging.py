"""
Модуль logging.py — настройки логирования для приложения.

Содержит класс LoggingSettings для централизованного хранения и доступа к параметрам логирования,
включая уровни логов, форматы, параметры файлового и консольного логирования, а также генерацию
конфигурации для logging.dictConfig().

Экспортируемые объекты:
- LoggingSettings: Класс настроек логирования (через pydantic).
"""

import os
from typing import Any

from pydantic_settings import BaseSettings


class LoggingSettings(BaseSettings):
    """
    Конфигурация логирования приложения.

    Атрибуты:
        LOG_LEVEL (str): Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        LOG_FORMAT (str): Формат логирования (pretty, json, simple).
        LOG_FILE (str): Путь к файлу логов.
        MAX_BYTES (int): Максимальный размер файла логов для ротации.
        BACKUP_COUNT (int): Количество резервных копий логов.
        ENCODING (str): Кодировка файла логов.
        FILE_MODE (str): Режим открытия файла логов.
        CONSOLE_ENABLED (bool): Включено ли логирование в консоль.
    """

    LOG_LEVEL: str = "DEBUG"
    LOG_FORMAT: str = "pretty"  # pretty, json, simple
    LOG_FILE: str = "./logs/app.log" if os.name == "nt" else "/var/log/app.log"
    MAX_BYTES: int = 10485760  # 10MB
    BACKUP_COUNT: int = 5
    ENCODING: str = "utf-8"
    FILE_MODE: str = "a"

    CONSOLE_ENABLED: bool = True

    # Трассировка SQL запросов (для отладки производительности)
    ENABLE_SQL_TRACING: bool = True

    FILE_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    PRETTY_FORMAT: str = (
        "\033[1;36m%(asctime)s\033[0m - \033[1;32m%(name)s\033[0m - \033[1;33m%(levelname)s\033[0m - %(message)s"
    )

    JSON_FORMAT: dict = {
        "timestamp": "%(asctime)s",
        "level": "%(levelname)s",
        "module": "%(module)s",
        "func": "%(funcName)s",
        "message": "%(message)s",
    }

    SIMPLE_FORMAT: str = "%(levelname)s - %(name)s - %(message)s"

    @property
    def current_format(self) -> str:
        """Возвращает текущий формат логирования"""
        format_map = {
            "pretty": self.PRETTY_FORMAT,
            "simple": self.SIMPLE_FORMAT,
            "json": self.FILE_FORMAT,
        }
        return format_map.get(self.LOG_FORMAT, self.FILE_FORMAT)

    @property
    def is_json_format(self) -> bool:
        """Проверяет, используется ли JSON формат"""
        return self.LOG_FORMAT.lower() == "json"

    @property
    def log_dir(self) -> str:
        """Возвращает директорию для логов"""
        return os.path.dirname(self.LOG_FILE)

    def ensure_log_dir(self) -> None:
        """Создает директорию для логов если она не существует"""
        log_dir = self.log_dir
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

    @property
    def file_handler_config(self) -> dict[str, Any]:
        """Конфигурация для файлового обработчика логов"""
        return {
            "filename": self.LOG_FILE,
            "maxBytes": self.MAX_BYTES,
            "backupCount": self.BACKUP_COUNT,
            "encoding": self.ENCODING,
            "mode": self.FILE_MODE,
        }

    @property
    def console_handler_config(self) -> dict[str, Any]:
        """Конфигурация для консольного обработчика логов"""
        return {
            "stream": "ext://sys.stdout",
        }

    def to_dict(self) -> dict[str, Any]:
        """Возвращает конфигурацию в виде словаря для настройки логирования"""
        return {
            "level": self.LOG_LEVEL,
            "format": self.current_format,
            "is_json": self.is_json_format,
            "console_enabled": self.CONSOLE_ENABLED,
            "file_config": self.file_handler_config,
            "console_config": self.console_handler_config,
        }

    @property
    def logging_config(self) -> dict[str, Any]:
        """
        Полная конфигурация для logging.dictConfig().

        Формирует структуру для dictConfig с учётом выбранного формата, ротации файлов и консольного вывода.
        """
        config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": self.current_format,
                },
            },
            "handlers": {},
            "root": {
                "level": self.LOG_LEVEL,
                "handlers": [],
            },
        }

        # Добавляем файловый обработчик
        if self.LOG_FILE:
            self.ensure_log_dir()
            config["handlers"]["file"] = {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "default",
                **self.file_handler_config,
            }
            config["root"]["handlers"].append("file")

        # Добавляем консольный обработчик
        if self.CONSOLE_ENABLED:
            config["handlers"]["console"] = {
                "class": "logging.StreamHandler",
                "formatter": "default",
                **self.console_handler_config,
            }
            config["root"]["handlers"].append("console")

        # Для JSON формата добавляем специальный форматтер
        if self.is_json_format:
            config["formatters"]["json"] = {
                "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(name)s %(levelname)s %(module)s %(funcName)s %(message)s",
            }
            # Применяем JSON форматтер ко всем обработчикам
            for handler in config["handlers"].values():
                handler["formatter"] = "json"

        return config

    class Config:
        extra = "ignore"
