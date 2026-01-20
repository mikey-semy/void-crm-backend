import os
import subprocess
from pathlib import Path
from typing import Optional
import socket
import threading
import platform
import sys
import time
import asyncio
import uvicorn


TEST_ENV_FILE = ".env.test"
DEV_ENV_FILE=".env.dev"

ROOT_DIR = Path(__file__).parents[1]

COMPOSE_FILE_WITHOUT_BACKEND = "docker-compose.dev.yml"
COMPOSE_FILE_WITHOUT_BACKEND_TEST = "docker-compose.test.yml"

# Порты для DEV инфраструктуры (стартовые значения для автопоиска)
# API_PORT читается из .env.dev в dev() функции
DEFAULT_PORTS = {
    'FASTAPI': 8000,  # Будет перезаписан из API_PORT в .env.dev
    'POSTGRES': 5432,
    'REDIS': 6379,
}

# Порты для TEST инфраструктуры (стартовые значения для автопоиска)
TEST_PORTS = {
    'FASTAPI': 8000,
    'POSTGRES': 5433,
    'REDIS': 6380,
    'RABBITMQ': 5682,
    'RABBITMQ_UI': 15682,
    'PGADMIN': 5052,
}

def check():
    """
    Статическая проверка качества кода через Ruff.

    Выполняет проверку через ruff check с группировкой
    ошибок по категориям для удобного анализа.

    Returns:
        bool: True если проверки прошли без ошибок

    Note:
        Использует настройки из pyproject.toml [tool.ruff]
    """
    print("\n" + "=" * 60)
    print("🔍 ПРОВЕРКА КАЧЕСТВА КОДА (Ruff)")
    print("=" * 60)

    ruff_success = True

    try:
        # Запускаем ruff check
        result = subprocess.run(
            ["ruff", "check", "app/", "--output-format=grouped"],
            capture_output=True,
            text=True,
            cwd=ROOT_DIR
        )

        if result.returncode == 0:
            print("✅ Ruff check: ошибок не найдено")
        else:
            print("❌ Ruff check: найдены ошибки")
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
            ruff_success = False

    except FileNotFoundError:
        print("❌ Ruff не установлен. Установите: uv sync --dev")
        return False
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка Ruff: {e}")
        ruff_success = False

    # Проверка форматирования
    try:
        result = subprocess.run(
            ["ruff", "format", "--check", "app/"],
            capture_output=True,
            text=True,
            cwd=ROOT_DIR
        )

        if result.returncode == 0:
            print("✅ Ruff format: код отформатирован правильно")
        else:
            print("⚠️  Ruff format: требуется форматирование")
            print("   Запустите: uv run format")
            ruff_success = False

    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка проверки форматирования: {e}")
        ruff_success = False

    print("=" * 60 + "\n")
    return ruff_success


def format_code():
    """
    Автоматическое форматирование кода через Ruff.

    Запускает:
    1. ruff format src/ - форматирование Python кода
    2. ruff check --fix src/ - автоисправление lint ошибок

    Raises:
        subprocess.CalledProcessError: При ошибках форматирования

    Note:
        Изменяет файлы на месте без подтверждения.
        Использует настройки из pyproject.toml [tool.ruff]
    """
    print("\n" + "=" * 60)
    print("🎨 ФОРМАТИРОВАНИЕ КОДА (Ruff)")
    print("=" * 60)

    try:
        # Форматирование
        print("📝 Форматирование кода...")
        subprocess.run(
            ["ruff", "format", "app/"],
            check=True,
            cwd=ROOT_DIR
        )
        print("✅ Форматирование завершено")

        # Автоисправление lint ошибок
        print("🔧 Автоисправление lint ошибок...")
        subprocess.run(
            ["ruff", "check", "--fix", "app/"],
            check=False,  # Не падаем если есть неисправляемые ошибки
            cwd=ROOT_DIR
        )
        print("✅ Автоисправление завершено")

    except FileNotFoundError:
        print("❌ Ruff не установлен. Установите: uv sync --dev")
        raise
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка форматирования: {e}")
        raise

    print("=" * 60 + "\n")


def lint():
    """
    Полный цикл линтинга: форматирование + проверка.

    Последовательно вызывает format_code() и check() для
    автоматического исправления стиля и проверки качества кода.

    Note:
        Удобная команда для подготовки кода к коммиту
    """
    print("\n" + "=" * 60)
    print("🚀 ПОЛНЫЙ ЦИКЛ ЛИНТИНГА")
    print("=" * 60 + "\n")

    format_code()
    success = check()

    if success:
        print("✅ Код готов к коммиту!")
    else:
        print("⚠️  Исправьте ошибки перед коммитом")

    return success

def migrate():
    """
    Применение миграций базы данных через Alembic.

    Выполняет команду 'alembic upgrade head' для применения
    всех неприменённых миграций. Используется автоматически
    в start_infrastructure() и start_all().

    Raises:
        subprocess.CalledProcessError: При ошибках миграции

    Note:
        Требует настроенного alembic.ini и доступной БД
    """
    import sys

    try:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            check=False,
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            timeout=30
        )
        # Если миграции уже применены, это OK
        if result.returncode == 0 or "Already up to date" in result.stdout or "Context impl" in result.stdout:
            return
        # Если реальная ошибка, выводим её
        if result.returncode != 0:
            print(f"⚠️ Миграции вернули код {result.returncode}")
            if result.stderr:
                print(f"Ошибка: {result.stderr}")
            if result.stdout:
                print(f"Вывод: {result.stdout}")
    except subprocess.TimeoutExpired:
        print("⚠️ Миграции заняли слишком много времени, пропускаем...")
    except KeyboardInterrupt:
        print("⚠️ Миграции прерваны, пропускаем...")
    except Exception as e:
        print(f"⚠️ Ошибка миграций: {e}, пропускаем...")

def find_free_port(start_port: int = 8000) -> int:
    """
    Ищет первый свободный порт начиная с указанного.

    Используется для FastAPI сервера в dev режиме.
    Проверяет возможность bind на порт через socket.

    Args:
        start_port: Начальный порт для поиска

    Returns:
        int: Номер свободного порта

    Raises:
        RuntimeError: Если все порты до 65535 заняты
    """
    port = start_port
    while port < 65535:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            port += 1
    raise RuntimeError("Нет свободных портов!")

def is_port_free(port: int) -> bool:
    """
    Проверяет доступность конкретного порта.

    Используется для валидации портов из .env.dev перед запуском
    инфраструктуры. Возвращает булево значение вместо исключения.

    Args:
        port: Номер порта для проверки

    Returns:
        bool: True если порт свободен, False если занят
    """
    try:
        # Проверяем через bind на 0.0.0.0 (все интерфейсы)
        # НЕ используем SO_REUSEADDR - иначе будет false positive!
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('0.0.0.0', port))
            return True
    except OSError:
        return False

def get_available_port(default_port: int) -> int:
    """
    Аналог find_free_port но с другим сообщением об ошибке.

    Дублирует логику find_free_port. Используется для поиска
    портов инфраструктурных сервисов в start_infrastructure.

    Args:
        default_port: Предпочитаемый порт

    Returns:
        int: Свободный порт

    Raises:
        RuntimeError: С указанием конкретного порта в ошибке
    """
    port = default_port
    while port < 65535:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            port += 1
    raise RuntimeError(f"Не могу найти свободный порт после {default_port}")

def get_port(service: str) -> int:
    """
    Получает порт сервиса из переменных окружения или дефолтный.

    Преобразует имя сервиса в формат переменной окружения
    и ищет значение. Fallback на DEFAULT_PORTS.

    Args:
        service: Имя сервиса (например 'REDIS_PORT')

    Returns:
        int: Номер порта для сервиса

    Note:
        Убирает '_PORT' из имени и приводит к верхнему регистру
    """
    service_upper = service.upper().replace('_PORT', '')
    return int(os.getenv(service, DEFAULT_PORTS[service_upper]))

def get_postgres_real_port() -> int:
    """
    Получает реальный внешний порт PostgreSQL контейнера.

    Returns:
        int: Внешний порт PostgreSQL или 5432 если не найден
    """
    try:
        postgres_container = get_postgres_container_name()
        if postgres_container == "postgres":
            return 5432

        result = subprocess.run(
            ["docker", "port", postgres_container, "5432"],
            capture_output=True,
            text=True,
            check=True
        )

        # Формат вывода: 0.0.0.0:5432
        if result.stdout.strip():
            port_line = result.stdout.strip()
            external_port = port_line.split(':')[-1]
            return int(external_port)

        return 5432
    except Exception as e:
        print(f"⚠️ Не удалось получить порт PostgreSQL: {e}")
        return 5432

def check_services():
    """
    Проверяет готовность всех инфраструктурных сервисов.

    Вызывается после docker-compose up для ожидания полной
    готовности PostgreSQL. Использует
    разное количество попыток для разных сервисов.

    Returns:
        bool: True если все сервисы готовы, False при таймауте

    Note:
        PostgreSQL получает 30 попыток, остальные по 5
    """
    services_config = {
        'Redis': ('REDIS_PORT', 5),
        'PostgreSQL': ('POSTGRES_PORT', 30),
    }

    for service_name, (port_key, retries) in services_config.items():
        # Берем порт из переменных окружения (которые мы установили выше)
        port = int(os.environ.get(port_key, get_port(port_key)))
        if not check_service(service_name, port, retries):
            print(f"❌ {service_name} не доступен на порту {port}!")
            return False
    return True

def check_service(name: str, port: int, retries: int = 10, delay: int = 3) -> bool:
    """
    Проверяет доступность сервиса через TCP подключение.

    Базовая функция для ожидания готовности сервисов после
    запуска контейнеров. Делает несколько попыток с задержкой.

    Args:
        name: Имя сервиса для логирования
        port: Порт для подключения
        retries: Количество попыток
        delay: Задержка между попытками в секундах

    Returns:
        bool: True если сервис отвечает, False если недоступен
    """
    # Увеличиваем количество попыток для PostgreSQL на macOS
    if name == "PostgreSQL" and platform.system() == "Darwin":
        retries = min(retries * 2, 60)  # Удваиваем, но не более 60
        print(f"🍎 macOS: увеличиваем время ожидания PostgreSQL до {retries} попыток")

    for attempt in range(retries):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)  # Увеличиваем таймаут
                result = sock.connect_ex(('localhost', port))
                if result == 0:
                    print(f"✅ {name} готов на порту {port}!")
                    return True
        except Exception as e:
            pass

        if attempt < retries - 1:  # Не показываем сообщение на последней попытке
            print(f"⏳ Ждём {name} на порту {port}... ({attempt + 1}/{retries})")
            time.sleep(delay)

    print(f"❌ {name} не готов после {retries} попыток")
    return False

def show_loader(message: str, stop_event: threading.Event):
    """
    Показывает анимированный loader

    Args:
        message: Сообщение для отображения
        stop_event: Событие для остановки анимации
    """
    chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    i = 0
    while not stop_event.is_set():
        sys.stdout.write(f'\r{chars[i % len(chars)]} {message}')
        sys.stdout.flush()
        time.sleep(0.1)
        i += 1
    sys.stdout.write('\r' + ' ' * (len(message) + 2) + '\r')
    sys.stdout.flush()

def debug_env_vars(env_file_path: str = None):
    """
    Выводит все переменные окружения связанные с БД для отладки.
    """
    print("\n" + "="*60)
    print("🔍 ОТЛАДКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ")
    print("="*60)

    # Проверяем переменные из .env файлов
    env_vars = load_env_vars(env_file_path=env_file_path)
    print(f"📁 Загружено из .env файла:")
    for key in ['POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_HOST', 'POSTGRES_PORT', 'POSTGRES_DATABASE']:
        value = env_vars.get(key, 'НЕ НАЙДЕНО')
        if 'PASSWORD' in key:
            print(f"   {key}: {'*' * len(str(value)) if value != 'НЕ НАЙДЕНО' else value}")
        else:
            print(f"   {key}: {value}")

    # Проверяем системные переменные окружения
    print(f"\n🖥️ Системные переменные окружения:")
    for key in ['POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_HOST', 'POSTGRES_PORT', 'POSTGRES_DATABASE']:
        value = os.environ.get(key, 'НЕ НАЙДЕНО')
        if 'PASSWORD' in key:
            print(f"   {key}: {'*' * len(str(value)) if value != 'НЕ НАЙДЕНО' else value}")
        else:
            print(f"   {key}: {value}")

    # Проверяем что видит settings
    try:
        from app.core.settings import settings
        print(f"\n⚙️ Что видит Settings:")
        print(f"   POSTGRES_USER: {settings.POSTGRES_USER}")
        print(f"   POSTGRES_PASSWORD: {'*' * len(settings.POSTGRES_PASSWORD.get_secret_value())}")
        print(f"   POSTGRES_HOST: {settings.POSTGRES_HOST}")
        print(f"   POSTGRES_PORT: {settings.POSTGRES_PORT}")
        print(f"   POSTGRES_DATABASE: {settings.POSTGRES_DATABASE}")
        print(f"   DATABASE_URL: {settings.database_url}")
    except Exception as e:
        print(f"   ❌ Ошибка загрузки settings: {e}")

    # Проверяем реальный порт PostgreSQL
    real_postgres_port = get_postgres_real_port()
    print(f"\n🐳 Реальный порт PostgreSQL: {real_postgres_port}")

    # Проверяем доступность PostgreSQL на реальном порту
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            result = s.connect_ex(('localhost', real_postgres_port))
            if result == 0:
                print(f"✅ PostgreSQL доступен на localhost:{real_postgres_port}")
            else:
                print(f"❌ PostgreSQL недоступен на localhost:{real_postgres_port}")
    except Exception as e:
        print(f"❌ Ошибка проверки PostgreSQL: {e}")

    print("="*60 + "\n")

def create_database(env_file_path: str = None):
    """
    Создаёт базу данных если она не существует.

    Поддерживает два режима:
    1. Через Docker exec в контейнер PostgreSQL
    2. Прямое подключение через psql (если Docker недоступен)

    Получает настройки из .env.dev, проверяет существование БД
    через SQL запрос, создаёт если отсутствует.

    Returns:
        bool: True при успехе, False при ошибке

    Note:
        Использует PGPASSWORD для передачи пароля в psql
    """
    print("🛠️ Проверяем наличие базы данных...")

    # Получаем данные из переменных окружения
    db_config = load_env_vars(env_file_path=env_file_path)

    # Получаем имя контейнера PostgreSQL динамически
    postgres_container = get_postgres_container_name()
    print(f"🔍 Используем PostgreSQL: {postgres_container}")

    # Извлекаем настройки БД
    user = db_config.get('POSTGRES_USER', 'postgres')
    password = db_config.get('POSTGRES_PASSWORD', '')
    host = db_config.get('POSTGRES_HOST', 'localhost')
    port = db_config.get('POSTGRES_PORT', '5432')
    db_name = db_config.get('POSTGRES_DATABASE', 'swpt_api_authenticate_db')

    try:
        # Проверяем, доступен ли Docker
        which_docker = subprocess.run(["which", "docker"], capture_output=True)
        docker_available = which_docker.returncode == 0

        if docker_available:
            # Специальная задержка для macOS - PostgreSQL медленно стартует
            if platform.system() == "Darwin":
                print("🍎 macOS обнаружена - добавляем дополнительную задержку для PostgreSQL...")
                time.sleep(10)

            # Ждём готовности PostgreSQL в контейнере
            print("⏳ Ждём готовности PostgreSQL...")
            postgres_ready = False
            max_retries = 30
            retry_count = 0

            while not postgres_ready and retry_count < max_retries:
                try:
                    # Проверяем готовность PostgreSQL
                    ready_check = subprocess.run(
                        ["docker", "exec", "-i", postgres_container, "pg_isready", "-U", user],
                        capture_output=True, text=True, timeout=5
                    )

                    if ready_check.returncode == 0:
                        postgres_ready = True
                        print("✅ PostgreSQL готов к работе!")
                    else:
                        retry_count += 1
                        print(f"⏳ PostgreSQL ещё не готов ({retry_count}/{max_retries})...")
                        time.sleep(2)

                except subprocess.TimeoutExpired:
                    retry_count += 1
                    print(f"⏳ Таймаут проверки PostgreSQL ({retry_count}/{max_retries})...")
                    time.sleep(2)
                except Exception as e:
                    retry_count += 1
                    print(f"⏳ Ошибка проверки PostgreSQL ({retry_count}/{max_retries}): {e}")
                    time.sleep(2)

            if not postgres_ready:
                print("❌ PostgreSQL не готов после ожидания!")
                return False

            # Проверяем существование базы данных
            check_db_inside = subprocess.run(
                ["docker", "exec", "-i", postgres_container, "psql", "-U", user, "-c",
                f"SELECT 1 FROM pg_database WHERE datname = '{db_name}';"],
                capture_output=True, text=True
            )

            if "1 row" not in check_db_inside.stdout:
                print(f"🛠️ База данных {db_name} не найдена внутри контейнера, создаём...")
                create_cmd = [
                    "docker", "exec", "-i", postgres_container, "psql", "-U", user, "-c",
                    f"CREATE DATABASE {db_name};"
                ]
                subprocess.run(create_cmd, check=True)
                print(f"✅ База данных {db_name} создана внутри контейнера!")
            else:
                print(f"✅ База данных {db_name} существует внутри контейнера!")
        else:
            # Прямое подключение через psql
            print(f"🔄 Проверяем БД напрямую через psql...")

            # Формируем команду для проверки существования БД
            psql_command = f"psql -U {user} -h {host} -p {port}"
            if password:
                # Установка переменной окружения PGPASSWORD для передачи пароля
                env = os.environ.copy()
                env["PGPASSWORD"] = password
            else:
                env = os.environ.copy()

            # Проверяем существование БД
            check_db = subprocess.run(
                f"{psql_command} -c \"SELECT 1 FROM pg_database WHERE datname = '{db_name}';\"",
                shell=True, env=env, capture_output=True, text=True
            )

            if "1 row" not in check_db.stdout:
                print(f"🛠️ База данных {db_name} не найдена, создаём...")
                create_cmd = f"{psql_command} -c \"CREATE DATABASE {db_name};\""
                subprocess.run(create_cmd, shell=True, env=env, check=True)
                print(f"✅ База данных {db_name} создана!")
            else:
                print(f"✅ База данных {db_name} существует!")

        # Выводим информацию о подключении
        dsn = f"postgresql://{user}:*******@{host}:{port}/{db_name}"
        print(f"🔄 Информация о подключении к БД: {dsn} (пароль скрыт)")

        return True
    except Exception as e:
        print(f"❌ Ошибка при работе с базой данных: {e}")
        return False

def get_postgres_container_name() -> str:
    """
    Определяет имя контейнера PostgreSQL или fallback для прямого подключения.

    Пытается найти запущенный контейнер через docker ps с фильтром по имени.
    Если Docker недоступен или контейнер не найден - возвращает "postgres"
    для прямого подключения к локальной БД.

    Returns:
        str: Имя контейнера PostgreSQL или "postgres" для прямого подключения

    Note:
        Используется в create_database() для выбора метода подключения
    """
    try:
        # Проверяем, доступен ли Docker
        which_result = subprocess.run(
            ["which", "docker"],
            capture_output=True,
            text=True
        )
        if which_result.returncode != 0:
            print("ℹ️ Docker не найден, используем прямое подключение к PostgreSQL")
            return "postgres"  # Стандартное имя для прямого подключения

        result = subprocess.run(
            ["docker", "ps", "--filter", "name=postgres", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            check=True
        )
        containers = [name for name in result.stdout.strip().split('\n') if name]
        if not containers:
            print("⚠️ Контейнер PostgreSQL не найден через Docker, используем прямое подключение")
            return "postgres"
        return containers[0]  # Берем первый найденный контейнер
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Ошибка при поиске контейнера PostgreSQL через Docker: {e}")
        return "postgres"
    except Exception as e:
        print(f"⚠️ Непредвиденная ошибка: {e}")
        return "postgres"

def test_db_connection(env_file_path: str = None):
    """
    Тестирует подключение к базе данных с текущими настройками.
    Можно явно указать env_file_path для тестовой среды.
    """
    print("🔌 Тестируем подключение к БД...")

    # Явно загружаем переменные окружения из нужного env-файла
    if env_file_path:
        load_env_vars(env_file_path=env_file_path, set_os_environ=True)

    try:
        from app.core.settings import settings
        import asyncpg

        async def test_connection():
            try:
                conn = await asyncpg.connect(
                    user=settings.POSTGRES_USER,
                    password=settings.POSTGRES_PASSWORD.get_secret_value(),
                    host=settings.POSTGRES_HOST,
                    port=settings.POSTGRES_PORT,
                    database='postgres'
                )
                print("✅ Подключение к PostgreSQL успешно!")
                await conn.close()
                return True
            except Exception as e:
                print(f"❌ Ошибка подключения к PostgreSQL: {e}")
                return False

        return asyncio.run(test_connection())
    except Exception as e:
        print(f"❌ Ошибка при тестировании подключения: {e}")
        return False

def serve(port: int = None):
    """
    Запуск только FastAPI сервера без инфраструктуры.

    Альтернатива dev() когда инфраструктура уже запущена
    или используется внешняя. Запускает uvicorn через subprocess
    с продакшн настройками (proxy-headers, forwarded-allow-ips).

    Args:
        port: Порт для сервера. Если None - автопоиск
    """
    if port is None:
        port = find_free_port()
    print(f"🚀 Запускаем сервер на порту {port}")
    subprocess.run([
        "uvicorn",
        "app.main:app",
        "--host", "0.0.0.0",
        "--port", str(port),
        "--proxy-headers",
        "--forwarded-allow-ips=*"
    ], check=True)

def start_all():
    """
    Быстрый старт: миграции + сервер без инфраструктуры.

    Альтернатива dev() когда инфраструктура уже запущена.
    Применяет миграции и запускает сервер через serve().

    Note:
        Не проверяет доступность БД перед миграциями
    """
    migrate()
    serve()

def activate():
    """
    Активация виртуального окружения через системные скрипты.

    Запускает платформо-специфичные скрипты активации:
    - Windows: scripts/activate.ps1 через PowerShell
    - Unix/Linux: scripts/activate.sh через Bash

    Note:
        Обычно вызывается после setup() для подготовки
        окружения к разработке
    """
    try:
        # Установка прав на выполнение для скриптов
        if platform.system() != "Windows":
            subprocess.run(["chmod", "+x", "scripts/activate.sh"], check=True)
            subprocess.run(["chmod", "+x", "scripts/setup.sh"], check=True)

        system = platform.system()
        if system == "Windows":
            subprocess.run(["powershell", "-File", "scripts/activate.ps1"], check=True)
        else:
            subprocess.run(["bash", "scripts/activate.sh"], check=True)
    except KeyboardInterrupt:
        print("\n🛑 Получен сигнал прерывания, завершаем работу...")
        sys.exit(0)
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка выполнения скрипта: {e}")
        sys.exit(1)

def setup():
    """
    Настройка окружения разработки через системные скрипты.

    Выбирает и запускает соответствующий скрипт установки
    в зависимости от операционной системы:
    - Windows: scripts/setup.ps1 через PowerShell
    - Unix/Linux: scripts/setup.sh через Bash

    Note:
        Скрипты должны содержать установку зависимостей,
        создание виртуального окружения, копирование .env файлов
    """
    system = platform.system()
    if system == "Windows":
        subprocess.run(["powershell", "-File", "scripts/setup.ps1"], check=True)
    else:
        subprocess.run(["bash", "scripts/setup.sh"], check=True)

def load_env_vars(env_file_path: str = None, set_os_environ: bool = True) -> dict:
    """
    Загружает переменные окружения из .env файла и (опционально) устанавливает их в os.environ.
    Args:
        env_file_path: Путь к файлу .env. Если None, используется тестовый файл
        set_os_environ: Если True, переменные будут добавлены в os.environ
    Returns:
        dict: Словарь с переменными окружения
    """
    if env_file_path is None:
        # Для тестов используем .env.test, если есть, иначе .env.dev
        dev_env_path = ROOT_DIR / DEV_ENV_FILE
        test_env_path = ROOT_DIR / TEST_ENV_FILE


        if dev_env_path.exists():
            env_file_path = str(dev_env_path)
            print(f"📋 Используем dev конфигурацию: {DEV_ENV_FILE}")
        elif test_env_path.exists():
            env_file_path = str(test_env_path)
            print(f"📋 Используем тестовую конфигурацию: {TEST_ENV_FILE}")
        else:
            print("❌ Не найден файл конфигурации (.env.dev или .env.test)")
            return {}

    env_vars = {}
    if os.path.exists(env_file_path):
        with open(env_file_path, encoding="utf-8") as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    try:
                        key, value = line.strip().split('=', 1)
                        # Убираем кавычки если есть
                        value = value.strip('"\'')
                        env_vars[key] = value
                        if set_os_environ:
                            os.environ[key] = value
                    except ValueError:
                        # Пропускаем некорректные строки
                        pass
    else:
        print(f"❌ Файл конфигурации не найден: {env_file_path}")

    return env_vars

def run_compose_command(command: str | list, compose_file: str = COMPOSE_FILE_WITHOUT_BACKEND, env: dict = None, env_file_path: str = None) -> None:
    """
    Запускает docker-compose команду в корне проекта

    Args:
        command: Команда для docker-compose
        compose_file: Путь к docker-compose файлу. По умолчанию используется COMPOSE_FILE_WITHOUT_BACKEND из констант
        env: Переменные окружения для docker-compose. По умолчанию используется DEV_ENV_FILE из констант

    Returns:
        None

    Raises:
        DockerDaemonNotRunningError: Если демон Docker не запущен
        DockerContainerConflictError: Если контейнер уже запущен
        FileNotFoundError: Если файл .env.dev или docker-compose файл не найден
    """
    if isinstance(command, str):
        command = command.split()

    # Проверяем наличие файла docker-compose
    compose_path = os.path.join(ROOT_DIR, compose_file)
    if not os.path.exists(compose_path):
        print(f"❌ Файл {compose_file} не найден в директории {ROOT_DIR}")
        raise FileNotFoundError(f"❌ Файл {compose_file} не найден в {ROOT_DIR}")

    # Проверяем наличие .env.dev
    env_path = os.path.join(ROOT_DIR, DEV_ENV_FILE)
    if not os.path.exists(env_path):
        print(f"❌ Файл {DEV_ENV_FILE} не найден в директории {ROOT_DIR}")
        print("💡 Создайте файл .env.dev с необходимыми переменными окружения")
        raise FileNotFoundError(f"❌ Файл {DEV_ENV_FILE} не найден. Создайте его перед запуском.")

    # Обновляем переменные окружения
    environment = os.environ.copy()
    # Добавляем переменные из DEV_ENV_FILE
    environment.update(load_env_vars(env_file_path=env_file_path))
    if env:
        environment.update(env)

    # show_output = any(cmd in command for cmd in ['up', 'build'])

    try:
        subprocess.run(
            ["docker-compose", "-f", compose_file] + command,
            cwd=ROOT_DIR,
            check=True,
            env=environment,
            # capture_output=not show_output,
            text=True
        )
    except subprocess.CalledProcessError as e:
        error_output = e.stderr or e.stdout or str(e)
        if "docker daemon is not running" in error_output or "pipe/docker_engine" in error_output:
            raise DockerDaemonNotRunningError() from e
        elif "Conflict" in error_output and "is already in use by container" in error_output:
            import re
            container_match = re.search(r'The container name "([^"]+)"', error_output)
            container_name = container_match.group(1) if container_match else None
            raise DockerContainerConflictError(container_name) from e
        raise

def dev(port: Optional[int] = None):
    """
    Основная команда для разработки - запуск полного стека.

    Выполняет полный цикл подготовки и запуска:
    1. Читает API_PORT из .env.dev или использует автопоиск
    2. start_infrastructure() - поднимает всю инфраструктуру
    3. uvicorn.run() - запускает сервер с hot reload

    Args:
        port: Конкретный порт для FastAPI. Если None - берёт из .env.dev или автопоиск

    Note:
        При ошибке инфраструктуры прерывает выполнение.
        Сервер запускается с debug логами и автоперезагрузкой
    """
    # Загружаем переменные окружения из .env.dev
    env_vars = load_env_vars(env_file_path=str(ROOT_DIR / DEV_ENV_FILE))

    # Находим порт для FastAPI: аргумент > API_PORT из .env > автопоиск
    if port is None:
        env_port = env_vars.get('API_PORT')
        if env_port:
            preferred_port = int(env_port)
            if is_port_free(preferred_port):
                port = preferred_port
                print(f"✅ Используем API_PORT из .env.dev: {port}")
            else:
                port = find_free_port(preferred_port)
                print(f"⚠️ Порт {preferred_port} занят, используем: {port}")
        else:
            port = find_free_port()

    # Запускаем инфраструктуру
    if not start_infrastructure(port):
        return


    print("\n" + "="*60)
    print("🚀 ЗАПУСК FASTAPI СЕРВЕРА")
    print("="*60)
    print(f"🌐 Адрес: http://localhost:{port}")
    print(f"📚 Документация: http://localhost:{port}/docs")
    print(f"🔄 Hot Reload: включён")
    print("="*60 + "\n")

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="debug",
        access_log=False
    )

def start_infrastructure(port: Optional[int] = None) -> bool:
    """
    Главная функция запуска инфраструктуры разработки.

    Полный цикл подготовки окружения:
    1. Проверка занятости портов из .env.dev
    2. Валидация Docker daemon
    3. Остановка старых контейнеров (down --remove-orphans)
    4. Очистка volumes
    5. Поиск свободных портов для всех сервисов
    6. Запуск контейнеров с новыми портами
    7. Ожидание готовности сервисов
    8. Выполнение миграций БД
    9. Вывод адресов сервисов

    Returns:
        bool: True при успешном запуске, False при ошибках

    Raises:
        DockerDaemonNotRunningError: Проблемы с Docker
        DockerContainerConflictError: Конфликты контейнеров
    """
    print("🚀 Запускаем инфраструктуру...")

    env_vars = load_env_vars(env_file_path=str(ROOT_DIR / DEV_ENV_FILE))

    # Автопоиск свободных портов для всех сервисов
    print("🔍 Ищем свободные порты для сервисов...")
    free_ports = {}
    for service, default_port in DEFAULT_PORTS.items():
        if service == 'FASTAPI':
            continue  # FASTAPI сам найдёт порт позже

        # Пытаемся использовать порт из .env.dev или дефолтный
        preferred_port = int(env_vars.get(f"{service}_PORT", default_port))

        if is_port_free(preferred_port):
            free_ports[service] = preferred_port
            print(f"   ✅ {service}: {preferred_port} (предпочитаемый)")
        else:
            # Ищем свободный порт начиная со следующего
            search_port = preferred_port + 1
            found_port = None
            max_attempts = 100  # Максимум 100 попыток

            for attempt in range(max_attempts):
                test_port = search_port + attempt
                if is_port_free(test_port):
                    found_port = test_port
                    break

            if found_port is None:
                print(f"   ❌ {service}: не удалось найти свободный порт после {max_attempts} попыток!")
                return False

            free_ports[service] = found_port
            print(f"   🔄 {service}: {found_port} (автопоиск, {preferred_port} занят)")

    # Обновляем DEFAULT_PORTS найденными свободными портами
    DEFAULT_PORTS.update(free_ports)

    try:
        # Проверяем статус Docker
        try:
            docker_info = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                check=True
            )
            print("✅ Docker запущен и работает")
        except subprocess.CalledProcessError as e:
            print("❌ Проблема с Docker:")
            if "permission denied" in str(e.stderr).lower():
                print("💡 Нет прав доступа к Docker. Попробуйте запустить от администратора.")
            elif "cannot connect to the docker daemon" in str(e.stderr).lower():
                print("💡 Docker Daemon не отвечает. Проверьте что:")
                print("   1. Docker Desktop точно запущен")
                print("   2. Служба Docker Engine работает")
                print("   3. Нет конфликтов с WSL или другими службами")
            raise DockerDaemonNotRunningError()

        # Проверяем запущенные контейнеры
        print("🔍 Проверяем запущенные контейнеры...")
        ps_result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            check=True
        )
        if ps_result.stdout.strip():
            print("⚠️ Найдены запущенные контейнеры:")
            for container in ps_result.stdout.strip().split('\n'):
                print(f"   - {container}")

        # Убиваем все контейнеры
        try:
            run_compose_command("down --remove-orphans")
        except subprocess.CalledProcessError as e:
            error_output = str(e)
            if "docker daemon is not running" in error_output or "pipe/docker_engine" in error_output:
                raise DockerDaemonNotRunningError()
            raise

        # На macOS дополнительно принудительно останавливаем все контейнеры
        if platform.system() == "Darwin":
            print("🍎 macOS: принудительная очистка контейнеров...")
            try:
                # Останавливаем все запущенные контейнеры
                ps_result = subprocess.run(["docker", "ps", "-q"], capture_output=True, text=True)
                if ps_result.stdout.strip():
                    container_ids = ps_result.stdout.strip().split('\n')
                    subprocess.run(["docker", "stop"] + container_ids, check=False, capture_output=True)
                    subprocess.run(["docker", "rm"] + container_ids, check=False, capture_output=True)
            except Exception as e:
                print(f"⚠️ Дополнительная очистка контейнеров: {e}")

        # Очищаем тома
        try:
            subprocess.run(["docker", "volume", "prune", "-f"], check=True)
        except subprocess.CalledProcessError as e:
            error_output = str(e)
            if "docker daemon is not running" in error_output or "pipe/docker_engine" in error_output:
                raise DockerDaemonNotRunningError()
            raise

        # Используем порты из DEFAULT_PORTS (уже содержат свободные порты после автопоиска)
        ports = DEFAULT_PORTS.copy()

        # Используем порты в docker-compose через переменные окружения
        env_for_compose = {
            f"{service}_PORT": str(p)
            for service, p in ports.items()
        }

        # ВАЖНО: Обновляем переменные окружения для текущего процесса
        # чтобы alembic и settings видели правильные порты
        os.environ.update(env_for_compose)

        print(f"🔍 Порты для запуска:")
        for service, p in ports.items():
            print(f"   {service}: {p}")

        # Запуск контейнеров с loader
        stop_loader = threading.Event()
        loader_thread = threading.Thread(target=show_loader, args=("", stop_loader))
        loader_thread.start()

        try:
            run_compose_command(["up", "-d"], COMPOSE_FILE_WITHOUT_BACKEND, env=env_for_compose, env_file_path=str(ROOT_DIR / DEV_ENV_FILE))
        except subprocess.CalledProcessError as e:
            error_output = str(e)
            if "docker daemon is not running" in error_output or "pipe/docker_engine" in error_output:
                raise DockerDaemonNotRunningError()
            elif "Conflict" in error_output and "is already in use by container" in error_output:
                # Извлекаем имя контейнера из сообщения об ошибке
                import re
                container_match = re.search(r'The container name "([^"]+)"', error_output)
                container_name = container_match.group(1) if container_match else None
                raise DockerContainerConflictError(container_name)
            raise
        finally:
            stop_loader.set()
            loader_thread.join()
            print("✅ Контейнеры запущены!")

        # Ждем доступности сервисов
        check_services()
        # Отладка переменных окружения
        debug_env_vars(env_file_path=str(ROOT_DIR / DEV_ENV_FILE))
        # Создаем базу данных после успешного поднятия PostgreSQL
        create_database(env_file_path=str(ROOT_DIR / DEV_ENV_FILE))
        # Запускаем миграции после успешного поднятия PostgreSQL
        test_db_connection(env_file_path=str(ROOT_DIR / DEV_ENV_FILE))

        print("📦 Запускаем миграции...")
        migrate()
        print("✅ Миграции выполнены!")

        print("\n" + "="*60)
        print("🎯 ИНФРАСТРУКТУРА ГОТОВА")
        print("="*60)

        print("\n📡 СЕРВИСЫ:")
        if port:
            print(f"📊 FastAPI Swagger:    http://localhost:{port}/docs")
        print(f"🗄️ PostgreSQL:        localhost:{ports['POSTGRES']}")
        print(f"📦 Redis:             localhost:{ports['REDIS']}")

        print("\n🔑 ДОСТУПЫ:")
        print(f"🗄️ PostgreSQL:        {env_vars.get('POSTGRES_USER', 'postgres')} / {env_vars.get('POSTGRES_PASSWORD', 'postgres')}")
        print(f"📦 Redis:             {env_vars.get('REDIS_PASSWORD', 'redispassword')}")

        return True
    except DockerDaemonNotRunningError as e:
        print(f"❌ {e}")
        print("💡 Запусти Docker Desktop и попробуй снова, олух.")
        return False
    except DockerContainerConflictError as e:
        print(f"❌ {e}")
        print("💡 Выполни следующую команду для удаления конфликтующих контейнеров:")
        print("```")
        print("docker rm -f $(docker ps -aq)")
        print("```")
        return False
    except Exception as e:
        print(f"❌ Ошибка при запуске инфраструктуры: {e}")
        return False

def infra_test():
    """
    Запуск только тестовой инфраструктуры (без тестов).

    Поднимает docker-compose.test.yml с отдельными портами:
    - PostgreSQL: 5433
    - Redis: 6380
    - RabbitMQ: 5682

    Note:
        Может работать параллельно с dev инфраструктурой
    """
    if not start_test_infrastructure():
        print("❌ Не удалось запустить тестовую инфраструктуру!")
        return
    print("✅ Тестовая инфраструктура готова!")


def test(coverage: bool = False, verbose: bool = True, path: str = None):
    """
    Запуск тестов через pytest.

    Args:
        coverage: Включить отчет о покрытии кода
        verbose: Подробный вывод
        path: Путь к тестам (по умолчанию tests/)

    Note:
        Проверяет доступность тестовой БД перед запуском.
        Для запуска инфраструктуры: uv run infra-test
    """
    print("\n" + "=" * 60)
    print("🧪 ЗАПУСК ТЕСТОВ")
    print("=" * 60)

    # Проверяем подключение к тестовой БД
    env_file_path = str(ROOT_DIR / TEST_ENV_FILE)
    if not test_db_connection(env_file_path=env_file_path):
        print("❌ Тестовая инфраструктура не готова!")
        print("   Запустите: uv run infra-test")
        return False

    print("✅ Тестовая БД доступна")
    print("🧪 Запускаю тесты...\n")

    # Формируем команду pytest
    cmd = ["pytest"]

    if verbose:
        cmd.append("-v")

    if coverage:
        cmd.extend(["--cov=app", "--cov-report=term-missing", "--cov-report=html"])

    if path:
        cmd.append(path)

    try:
        result = subprocess.run(cmd, cwd=ROOT_DIR)

        print("\n" + "=" * 60)
        if result.returncode == 0:
            print("✅ Все тесты прошли успешно!")
            if coverage:
                print("📊 Отчет о покрытии: htmlcov/index.html")
        else:
            print(f"❌ Тесты завершились с ошибками (код {result.returncode})")
        print("=" * 60 + "\n")

        return result.returncode == 0

    except FileNotFoundError:
        print("❌ pytest не установлен. Установите: uv sync --dev")
        return False
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка запуска тестов: {e}")
        return False

def start_test_infrastructure():
    """
    Запуск инфраструктуры для тестирования.

    Использует .env.test и отдельные порты (TEST_PORTS),
    которые не конфликтуют с DEV инфраструктурой.

    Полный цикл: проверка портов, запуск Docker, миграции.
    """
    print("\n" + "=" * 60)
    print("🧪 ЗАПУСК ТЕСТОВОЙ ИНФРАСТРУКТУРЫ")
    print("=" * 60)

    env_vars = load_env_vars(env_file_path=str(ROOT_DIR / TEST_ENV_FILE))

    # Автопоиск свободных портов для тестовой инфраструктуры
    print("🔍 Ищем свободные порты для тестовых сервисов...")
    free_ports = {}
    for service, default_port in TEST_PORTS.items():
        if service == 'FASTAPI':
            continue  # FASTAPI не запускаем в тестовой инфраструктуре

        preferred_port = int(env_vars.get(f"{service}_PORT", default_port))

        if is_port_free(preferred_port):
            free_ports[service] = preferred_port
            print(f"   ✅ {service}: {preferred_port} (предпочитаемый)")
        else:
            found_port = get_available_port(preferred_port + 1)
            free_ports[service] = found_port
            print(f"   🔄 {service}: {found_port} (автопоиск, {preferred_port} занят)")

    TEST_PORTS.update(free_ports)

    try:
        # Проверяем статус Docker
        try:
            docker_info = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                check=True
            )
            print("✅ Docker запущен и работает")
        except subprocess.CalledProcessError as e:
            print("❌ Проблема с Docker:")
            if "permission denied" in str(e.stderr).lower():
                print("💡 Нет прав доступа к Docker. Попробуйте запустить от администратора.")
            elif "cannot connect to the docker daemon" in str(e.stderr).lower():
                print("💡 Docker Daemon не отвечает. Проверьте что:")
                print("   1. Docker Desktop точно запущен")
                print("   2. Служба Docker Engine работает")
                print("   3. Нет конфликтов с WSL или другими службами")
            raise DockerDaemonNotRunningError()

        # Проверяем запущенные контейнеры
        print("🔍 Проверяем запущенные контейнеры...")
        ps_result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            check=True
        )
        if ps_result.stdout.strip():
            print("⚠️ Найдены запущенные контейнеры:")
            for container in ps_result.stdout.strip().split('\n'):
                print(f"   - {container}")

        # Останавливаем все контейнеры
        try:
            run_compose_command("down --remove-orphans", compose_file=COMPOSE_FILE_WITHOUT_BACKEND_TEST, env_file_path=str(ROOT_DIR / TEST_ENV_FILE))
        except subprocess.CalledProcessError as e:
            error_output = str(e)
            if "docker daemon is not running" in error_output or "pipe/docker_engine" in error_output:
                raise DockerDaemonNotRunningError()
            raise

        # Очищаем тома
        try:
            subprocess.run(["docker", "volume", "prune", "-f"], check=True)
        except subprocess.CalledProcessError as e:
            error_output = str(e)
            if "docker daemon is not running" in error_output or "pipe/docker_engine" in error_output:
                raise DockerDaemonNotRunningError()
            raise

        # Используем порты из TEST_PORTS (уже содержат свободные порты после автопоиска)
        ports = {k: v for k, v in TEST_PORTS.items() if k != 'FASTAPI'}

        env_for_compose = {
            f"{service}_PORT": str(port)
            for service, port in ports.items()
        }

        os.environ.update(env_for_compose)

        print(f"🔍 Порты для запуска:")
        for service, port in ports.items():
            print(f"   {service}: {port}")

        stop_loader = threading.Event()
        loader_thread = threading.Thread(target=show_loader, args=("", stop_loader))
        loader_thread.start()

        try:
            run_compose_command(
                ["up", "-d"],
                compose_file=COMPOSE_FILE_WITHOUT_BACKEND_TEST,
                env=env_for_compose,
                env_file_path=str(ROOT_DIR / TEST_ENV_FILE)
            )
        except subprocess.CalledProcessError as e:
            error_output = str(e)
            if "docker daemon is not running" in error_output or "pipe/docker_engine" in error_output:
                raise DockerDaemonNotRunningError()
            elif "Conflict" in error_output and "is already in use by container" in error_output:
                import re
                container_match = re.search(r'The container name "([^"]+)"', error_output)
                container_name = container_match.group(1) if container_match else None
                raise DockerContainerConflictError(container_name)
            raise
        finally:
            stop_loader.set()
            loader_thread.join()
            print("✅ Контейнеры запущены!")

        check_services()
        debug_env_vars(env_file_path=str(ROOT_DIR / TEST_ENV_FILE))
        create_database(env_file_path=str(ROOT_DIR / TEST_ENV_FILE))
        test_db_connection(env_file_path=str(ROOT_DIR / TEST_ENV_FILE))

        print("📦 Запускаем миграции...")
        migrate()
        print("✅ Миграции выполнены!")

        print("\n" + "="*60)
        print("🎯 ТЕСТОВАЯ ИНФРАСТРУКТУРА ГОТОВА")
        print("="*60)

        print("\n📡 СЕРВИСЫ:")
        print(f"🗄️ PostgreSQL:        localhost:{ports['POSTGRES']}")
        print(f"📦 Redis:             localhost:{ports['REDIS']}")

        print("\n🔑 ДОСТУПЫ:")
        print(f"🗄️ PostgreSQL:        {env_vars.get('POSTGRES_USER', 'postgres')} / {env_vars.get('POSTGRES_PASSWORD', 'postgres')}")
        print(f"📦 Redis:             {env_vars.get('REDIS_PASSWORD', 'redispassword')}")
        return True
    except DockerDaemonNotRunningError as e:
        print(f"❌ {e}")
        print("💡 Запусти Docker Desktop и попробуй снова, олух.")
        return False
    except DockerContainerConflictError as e:
        print(f"❌ {e}")
        print("💡 Выполни следующую команду для удаления конфликтующих контейнеров:")
        print("```")
        print("docker rm -f $(docker ps -aq)")
        print("```")
        return False
    except Exception as e:
        print(f"❌ Ошибка при запуске тестовой инфраструктуры: {e}")
        return False

def bootstrap():
    """
    Полная инициализация проекта с нуля.

    Выполняет:
    1. Остановку всех контейнеров
    2. Очистку volumes
    3. Запуск инфраструктуры
    4. Создание БД
    5. Миграции
    6. Загрузку фикстур
    """
    print("🚀 Полная инициализация проекта...")

    try:
        # Принудительно останавливаем ВСЕ контейнеры Docker
        print("🛑 Останавливаем все контейнеры...")
        try:
            # Сначала пробуем остановить через docker-compose
            run_compose_command("down --remove-orphans")
        except Exception as e:
            print(f"⚠️ Не удалось остановить через docker-compose: {e}")

        # Принудительно останавливаем все запущенные контейнеры
        try:
            subprocess.run(["docker", "stop", "$(docker ps -q)"], shell=True, check=False, capture_output=True)
            subprocess.run(["docker", "rm", "$(docker ps -aq)"], shell=True, check=False, capture_output=True)
        except Exception as e:
            print(f"⚠️ Не удалось остановить контейнеры напрямую: {e}")

        # Очищаем volumes и networks
        print("🧹 Очищаем volumes и networks...")
        try:
            subprocess.run(["docker", "volume", "prune", "-f"], check=False, capture_output=True)
            subprocess.run(["docker", "network", "prune", "-f"], check=False, capture_output=True)
        except Exception as e:
            print(f"⚠️ Не удалось очистить volumes/networks: {e}")

        # Проверяем что порты освободились
        print("🔍 Проверяем освобождение портов...")
        busy_ports = []
        for service, default_port in DEFAULT_PORTS.items():
            if service != 'FASTAPI':  # FASTAPI сам найдет свободный порт
                if not is_port_free(default_port):
                    busy_ports.append(f"{service}: {default_port}")

        if busy_ports:
            print("⚠️ Некоторые порты всё ещё заняты:")
            for port_info in busy_ports:
                print(f"   - {port_info}")
            print("🔄 Продолжаем с автопоиском свободных портов...")

        # Запускаем инфраструктуру (порт FastAPI не нужен, bootstrap не запускает сервер)
        if not start_infrastructure():
            print("❌ Не удалось запустить инфраструктуру!")
            return False

        print("✅ Проект полностью инициализирован!")
        return True

    except Exception as e:
        print(f"❌ Ошибка при инициализации: {e}")
        return False


def worker():
    """
    Запуск воркера для обработки фоновых задач из RabbitMQ.

    Воркер использует FastStream для подключения к RabbitMQ
    и обработки очередей (индексация статей, уведомления и т.д.).

    Note:
        Требует запущенной инфраструктуры (RabbitMQ, PostgreSQL).
        Использует .env.dev для локальной разработки.
    """
    print("\n" + "=" * 60)
    print("🔄 ЗАПУСК ВОРКЕРА")
    print("=" * 60)

    # Загружаем переменные окружения
    load_env_vars(env_file_path=str(ROOT_DIR / DEV_ENV_FILE))

    print("📋 Очереди:")
    print("   - knowledge_article_indexing (индексация статей)")
    print("=" * 60 + "\n")

    try:
        # Запускаем воркер
        subprocess.run(
            [sys.executable, "-m", "worker.main"],
            cwd=ROOT_DIR,
            check=True
        )
    except KeyboardInterrupt:
        print("\n🛑 Воркер остановлен по Ctrl+C")
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка запуска воркера: {e}")
        raise


class DockerDaemonNotRunningError(Exception):
    """
    Исключение, возникающее когда Docker демон не запущен или недоступен.
    """
    def __init__(self, message=None):
        self.message = message or "Docker демон не запущен. Убедись, что Docker Desktop запущен и работает."
        super().__init__(self.message)


class DockerContainerConflictError(Exception):
    """
    Исключение, возникающее при конфликте имен контейнеров Docker.
    """
    def __init__(self, container_name=None, message=None):
        if container_name:
            self.message = message or f"Конфликт имен контейнеров. Контейнер '{container_name}' уже используется. Удали его или переименуй."
        else:
            self.message = message or "Конфликт имен контейнеров. Удали существующий контейнер или переименуй его."
        super().__init__(self.message)
