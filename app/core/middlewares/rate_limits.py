"""Middleware для ограничения частоты запросов (rate limiting) с использованием Token Bucket."""

import logging
import time

from fastapi import Request
from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.exceptions import RateLimitExceededError
from app.core.settings import settings

# Lua-скрипт для атомарного выполнения Token Bucket алгоритма в Redis
# Аргументы:
#   KEYS[1] - ключ для хранения состояния бакета (например, "ratelimit:192.168.1.1")
#   ARGV[1] - capacity (максимальное количество токенов)
#   ARGV[2] - refill_rate (токенов в секунду)
#   ARGV[3] - current_time (текущее время в секундах с плавающей точкой)
#   ARGV[4] - cost (количество токенов для списания, обычно 1)
#
# Возвращает:
#   [allowed, tokens_remaining, reset_time]
#   - allowed: 1 если запрос разрешен, 0 если превышен лимит
#   - tokens_remaining: количество оставшихся токенов (после списания, если разрешено)
#   - reset_time: время в секундах до появления следующего токена
TOKEN_BUCKET_LUA_SCRIPT = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local current_time = tonumber(ARGV[3])
local cost = tonumber(ARGV[4])

-- Получаем текущее состояние из Redis
local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
local tokens = tonumber(bucket[1])
local last_refill = tonumber(bucket[2])

-- Если бакет не инициализирован, создаем его с полным количеством токенов
if tokens == nil then
    tokens = capacity
    last_refill = current_time
end

-- Вычисляем количество токенов для добавления с момента последнего обновления
local time_passed = current_time - last_refill
local tokens_to_add = time_passed * refill_rate

-- Обновляем количество токенов, но не превышаем capacity
tokens = math.min(capacity, tokens + tokens_to_add)

-- Проверяем, достаточно ли токенов для выполнения запроса
local allowed = 0
local reset_time = 0

if tokens >= cost then
    -- Списываем токены
    tokens = tokens - cost
    allowed = 1

    -- Обновляем состояние в Redis
    redis.call('HMSET', key, 'tokens', tokens, 'last_refill', current_time)

    -- Устанавливаем TTL для автоматической очистки неактивных ключей
    -- TTL = время до полного восстановления бакета + небольшой запас
    local ttl = math.ceil(capacity / refill_rate) + 60
    redis.call('EXPIRE', key, ttl)

    -- Вычисляем время до следующего токена (для заголовка X-RateLimit-Reset)
    if tokens < capacity then
        reset_time = math.ceil((1.0 / refill_rate))
    else
        reset_time = 0
    end
else
    -- Недостаточно токенов - запрос отклонен
    allowed = 0

    -- Вычисляем время ожидания до появления достаточного количества токенов
    local tokens_needed = cost - tokens
    reset_time = math.ceil(tokens_needed / refill_rate)

    -- Обновляем last_refill, чтобы не терять прогресс
    redis.call('HMSET', key, 'tokens', tokens, 'last_refill', current_time)

    local ttl = math.ceil(capacity / refill_rate) + 60
    redis.call('EXPIRE', key, ttl)
end

return {allowed, math.floor(tokens), reset_time}
"""


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware для ограничения частоты запросов к API с использованием алгоритма Token Bucket.

    Token Bucket позволяет:
    - Обрабатывать всплески трафика (burst) до capacity токенов
    - Поддерживать устойчивую скорость (sustained rate) = refill_rate токенов/сек
    - Корректно работать в кластерном окружении (состояние в Redis)

    Пример:
        capacity=100, refill_rate=2.0 означает:
        - Можно сделать до 100 запросов мгновенно (burst)
        - Затем скорость ограничена 2 запросами в секунду (sustained)
    """

    def __init__(
        self,
        app,
        capacity: int | None = None,
        refill_rate: float | None = None,
        redis_url: str | None = None,
        exclude_paths: list | None = None,
    ):
        """
        Инициализирует middleware для ограничения частоты запросов.

        Args:
            app: ASGI приложение
            capacity: Максимальное количество токенов в бакете (burst capacity)
            refill_rate: Скорость пополнения токенов (токенов в секунду)
            redis_url: URL для подключения к Redis
            exclude_paths: Список префиксов путей, которые не подлежат ограничению
        """
        super().__init__(app)

        # Получаем параметры из настроек
        default_params = settings.rate_limit_params
        self.capacity = capacity if capacity is not None else default_params.get("capacity", 100)
        self.refill_rate = refill_rate if refill_rate is not None else default_params.get("refill_rate", 2.0)
        redis_url = redis_url if redis_url is not None else default_params.get("redis_url")

        self.exclude_paths = tuple(
            exclude_paths if exclude_paths is not None else default_params.get("exclude_paths", [])
        )

        # Инициализируем Redis клиент
        self.redis: Redis | None = None
        self.redis_url = redis_url
        self._lua_script_sha: str | None = None  # SHA хеш загруженного Lua-скрипта

        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info(
            "RateLimitMiddleware инициализирован: capacity=%d, refill_rate=%.2f токенов/сек",
            self.capacity,
            self.refill_rate,
        )

    async def _ensure_redis_connection(self):
        """Ленивая инициализация подключения к Redis."""
        if self.redis is None:
            try:
                self.redis = Redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=False,  # Lua script возвращает числа
                )
                # Проверяем подключение
                await self.redis.ping()

                # Загружаем Lua-скрипт в Redis и сохраняем его SHA
                script_sha = await self.redis.script_load(TOKEN_BUCKET_LUA_SCRIPT)
                self._lua_script_sha = str(script_sha)  # Явное приведение для mypy

                self.logger.info("✅ Подключение к Redis установлено для RateLimitMiddleware")
            except Exception as e:
                self.logger.error(
                    "❌ Ошибка подключения к Redis для RateLimitMiddleware: %s",
                    str(e),
                    exc_info=True,
                )
                # Если Redis недоступен, middleware будет пропускать все запросы
                self.redis = None
                self._lua_script_sha = None

    async def _check_rate_limit(self, client_ip: str) -> tuple[bool, int, int]:
        """
        Проверяет rate limit для клиента с использованием Token Bucket алгоритма.

        Args:
            client_ip: IP-адрес клиента

        Returns:
            Tuple[bool, int, int]: (allowed, tokens_remaining, reset_time)
                - allowed: True если запрос разрешен
                - tokens_remaining: количество оставшихся токенов
                - reset_time: секунды до появления следующего токена
        """
        await self._ensure_redis_connection()

        if self.redis is None or self._lua_script_sha is None:
            # Если Redis недоступен, пропускаем все запросы (fail-open)
            self.logger.warning("Redis недоступен, rate limiting отключен")
            return True, self.capacity, 0

        try:
            # Ключ для хранения состояния бакета клиента
            key = f"ratelimit:token_bucket:{client_ip}"
            current_time = time.time()
            cost = 1  # Стоимость одного запроса в токенах

            try:
                # Выполняем Lua-скрипт атомарно
                # Type: evalsha возвращает list[Any] для Lua-скриптов, возвращающих массивы
                result: list = await self.redis.evalsha(  # type: ignore[misc]
                    self._lua_script_sha,
                    1,  # Количество ключей
                    key,
                    self.capacity,
                    self.refill_rate,
                    current_time,
                    cost,
                )
            except Exception as script_error:
                # Если скрипт не найден (Redis перезапущен), перезагружаем его
                if "No matching script" in str(script_error) or "NOSCRIPT" in str(script_error):
                    self.logger.warning("Lua скрипт потерян, перезагружаем...")
                    script_sha = await self.redis.script_load(TOKEN_BUCKET_LUA_SCRIPT)
                    self._lua_script_sha = str(script_sha)

                    # Повторяем попытку
                    result: list = await self.redis.evalsha(  # type: ignore[misc]
                        self._lua_script_sha,
                        1,
                        key,
                        self.capacity,
                        self.refill_rate,
                        current_time,
                        cost,
                    )
                else:
                    raise

            # Распаковываем результат
            allowed = bool(result[0])
            tokens_remaining = int(result[1])
            reset_time = int(result[2])

            return allowed, tokens_remaining, reset_time

        except Exception as e:
            self.logger.error(
                "Ошибка при проверке rate limit для %s: %s",
                client_ip,
                str(e),
                exc_info=True,
            )
            # В случае ошибки пропускаем запрос (fail-open)
            return True, self.capacity, 0

    async def dispatch(self, request: Request, call_next):
        """
        Обрабатывает запрос и применяет ограничение частоты.

        Args:
            request: Входящий HTTP-запрос
            call_next: Функция для передачи запроса следующему обработчику

        Returns:
            Response: HTTP-ответ
        """
        # Проверяем, нужно ли применять ограничение к данному пути
        path = request.url.path
        if any(path.startswith(exclude_path) for exclude_path in self.exclude_paths):
            return await call_next(request)

        # Получаем IP-адрес клиента
        client_ip = "unknown"
        if request.client and request.client.host:
            client_ip = request.client.host
        else:
            # Fallback для прокси
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                client_ip = forwarded.split(",")[0].strip()

        # Проверяем rate limit
        allowed, tokens_remaining, reset_time = await self._check_rate_limit(client_ip)

        if not allowed:
            # Превышен лимит запросов
            self.logger.warning(
                "Превышен лимит запросов для IP %s",
                client_ip,
                extra={
                    "client_ip": client_ip,
                    "path": path,
                    "method": request.method,
                    "tokens_remaining": tokens_remaining,
                    "reset_time": reset_time,
                },
            )
            raise RateLimitExceededError(reset_time=reset_time)

        # Передаем запрос дальше
        response = await call_next(request)

        # Добавляем заголовки с информацией о лимитах
        response.headers["X-RateLimit-Limit"] = str(self.capacity)
        response.headers["X-RateLimit-Remaining"] = str(tokens_remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)

        return response

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_redis_connection()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - закрываем Redis соединение."""
        if self.redis is not None:
            await self.redis.close()
            self.logger.info("Redis соединение закрыто для RateLimitMiddleware")
