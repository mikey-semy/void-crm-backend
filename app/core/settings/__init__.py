"""
Модуль инициализации настроек приложения.

Этот модуль предоставляет глобальный доступ к объекту настроек приложения (`settings`),
используя кэширование через декоратор `lru_cache`. Это гарантирует, что объект настроек
(`Settings`) создаётся только один раз за время жизни процесса, даже при многократных
импортах или вызовах. Такой подход экономит ресурсы и предотвращает повторную загрузку
или парсинг конфигурации.

Экспортируемые объекты:
- settings: Глобальный экземпляр настроек приложения.
- Settings: Класс настроек приложения.
"""

from functools import lru_cache

from .base import Settings
from .logging import LoggingSettings
from .paths import PathSettings


class CompositeSettings(Settings):
    """Композитный класс настроек."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.paths = PathSettings()
        self.logging = LoggingSettings()


@lru_cache
def get_settings() -> CompositeSettings:
    """Получение настроек приложения из кэша."""
    return CompositeSettings()


settings = get_settings()

__all__ = ["settings", "Settings"]
