"""
Модуль paths.py — вспомогательный модуль для управления путями и определением окружения.

Назначение:
1. Автоматически определяет корневую директорию проекта по маркерным файлам (например, .git, pyproject.toml, README.md).
2. Предоставляет централизованные пути к основным директориям приложения (app, core).
3. Определяет, какой файл переменных окружения использовать (.env, .env.dev, .env.test или кастомный), и возвращает его путь и тип окружения.

Экспортируемые объекты:
- PathSettings: Класс с утилитами для работы с путями и окружением.
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class PathSettings:
    """
    Класс для централизованного управления путями и определением типа окружения.

    Атрибуты класса:
        PROJECT_ROOT (Path): Корневая директория проекта.
        APP_DIR (Path): Директория с исходным кодом приложения (app).
        CORE_DIR (Path): Директория с ядром приложения (app/core).
    """

    @staticmethod
    def find_project_root() -> Path:
        """
        Находит корень проекта по маркерным файлам.

        Алгоритм:
        - Начинает поиск с текущей рабочей директории.
        - Поднимается вверх по дереву директорий.
        - Если находит хотя бы один из маркерных файлов (.git, pyproject.toml, README.md), возвращает эту директорию.
        - Если ни один маркер не найден, возвращает текущую директорию и пишет предупреждение в лог.

        Returns:
            Path: Путь к корню проекта.
        """
        current_dir = Path.cwd()

        # Маркерные файлы, которые обычно есть в корне проекта
        markers = [".git", "pyproject.toml", "README.md"]

        # Ищем маркеры, поднимаясь по директориям
        for parent in [current_dir, *current_dir.parents]:
            if any((parent / marker).exists() for marker in markers):
                return parent

        logger.warning("Не удалось определить корень проекта, используем текущую директорию")
        return current_dir

    PROJECT_ROOT = find_project_root()

    APP_DIR = PROJECT_ROOT / "app"
    CORE_DIR = APP_DIR / "core"
    DATA_DIR = PROJECT_ROOT / "data"
    FIXTURES_DIR = DATA_DIR / "fixtures"

    @staticmethod
    def get_env_file_and_type() -> tuple[Path, str]:
        """
        Определяет путь к файлу с переменными окружения и тип окружения.

        Алгоритм:
        - Если переменная окружения ENVIRONMENT задана (test/production), используется .env.test или .env.
        - Если переменная окружения ENV_FILE задана, используется указанный путь.
        - Если в корне проекта есть .env.dev, используется он и считается development-окружением.
        - В остальных случаях используется .env и считается production-окружением.

        Returns:
            tuple[Path, str]: Путь к файлу с переменными окружения и тип окружения (development/production/test/custom).
        """
        env_file = Path(".env")
        dev_env_file = Path(".env.dev")
        test_env_file = Path(".env.test")

        # Определяем конфигурацию
        environment = os.getenv("ENVIRONMENT")
        env_file_path = os.getenv("ENV_FILE")

        if environment:
            # ENVIRONMENT имеет приоритет
            if environment.lower() == "test":
                env_path = test_env_file
                env_type = "test"
            elif environment.lower() == "production":
                env_path = env_file
                env_type = "production"
            elif environment.lower() == "development":
                env_path = dev_env_file
                env_type = "development"
            else:
                env_path = env_file
                env_type = "production"
        elif env_file_path:
            env_path = Path(env_file_path)
            if ".env.test" in str(env_path):
                env_type = "test"
            else:
                env_type = "custom"
        elif dev_env_file.exists():
            env_path = dev_env_file
            env_type = "development"
        else:
            env_path = env_file
            env_type = "production"

        logger.info("Запуск в режиме: %s", env_type.upper())
        logger.info("Конфигурация: %s", env_path)

        return env_path, env_type
