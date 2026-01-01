"""
Модуль зависимостей приложения.

Этот модуль содержит базовый класс для зависимостей, которые будут использоваться
в приложении. Он определяет общий интерфейс для всех зависимостей и обеспечивает
обработку ошибок и логирование.

Classes:
    - BaseDependency: Базовый класс для зависимостей приложения.

Exceptions:
    - ServiceUnavailableException: Кастомное исключение, выбрасываемое при
      недоступности сервиса.
"""

import logging
from abc import ABC, abstractmethod

from src.core.exceptions import ServiceUnavailableException


class BaseDependency(ABC):
    """
    Базовый класс для зависимостей в приложении.

    Этот класс определяет общий интерфейс для всех зависимостей, которые
    будут использоваться в приложении. Он обеспечивает обработку ошибок
    и логирование, а также требует реализации метода получения зависимости.

    Attributes:
        None
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def get_dependency(self, *args, **kwargs):
        """
        Метод для получения зависимости.

        Этот метод должен быть реализован в подклассах и возвращать
        экземпляр зависимости, необходимой для работы сервиса.

        Args:
            *args: Позиционные аргументы, которые могут быть переданы
                в зависимости от конкретной реализации.
            **kwargs: Именованные аргументы, которые могут быть переданы
                в зависимости от конкретной реализации.

        Returns:
            Объект зависимости, необходимый для работы сервиса.

        Raises:
            NotImplementedError: Если метод не реализован в подклассе.
        """
        pass

    async def handle_exception(self, e: Exception, service_name: str):
        """
        Обработка исключений с использованием кастомного исключения.

        Этот метод логирует ошибку и выбрасывает кастомное исключение
        ServiceUnavailableException, если возникает ошибка при получении
        зависимости.

        Args:
            e (Exception): Исключение, которое нужно обработать.
            service_name (str): Имя сервиса, для которого возникла ошибка.

        Raises:
            ServiceUnavailableException: Если возникает ошибка при получении зависимости.
        """
        self.logger.error("Ошибка получения зависимости %s: %s", service_name, e, exc_info=True)
        raise ServiceUnavailableException(service_name=service_name)
