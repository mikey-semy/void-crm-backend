# Monitoring & Tracing

Система трассировки запросов и мониторинга производительности через query hooks.

## 📊 Query Hooks

Query hooks позволяют отслеживать метрики выполнения запросов к БД.

### Включение трассировки

**Простой способ:**
```python
>>> # При создании репозитория
>>> repo = ProductRepository(
...     session,
...     ProductModel,
...     enable_tracing=True  # Автоматически добавляет LoggingHook
... )
>>>
>>> # Теперь все запросы логируются
>>> products = await repo.filter_by(is_active=True)
>>> # INFO: Query 'select' for ProductModel: 45.2ms, 150 rows
```

---

## 🎣 Встроенные Hooks

### `LoggingHook`

Базовый хук для логирования метрик.

**Инициализация:**
```python
>>> from src.repository.monitoring import LoggingHook
>>>
>>> hook = LoggingHook(
...     slow_query_threshold_ms=100,  # Порог медленного запроса
...     log_query_params=False  # Логировать ли параметры
... )
>>>
>>> repo.add_hook(hook)
```

**Параметры:**
- `slow_query_threshold_ms` - порог медленного запроса в мс (по умолчанию 100)
- `log_query_params` - логировать ли параметры запроса (по умолчанию False)

**Уровни логирования:**
- `ERROR` - если произошла ошибка
- `WARNING` - медленный запрос (> threshold)
- `INFO` - обычный запрос

**Примеры логов:**
```
INFO: Query 'select' for ProductModel: 45.2ms, 150 rows
WARNING: SLOW Query 'select' for CategoryModel: 250.5ms, 1000 rows
ERROR: Query 'update' for ProductModel: 15.2ms, 0 rows ERROR: not found
```

---

### `DetailedLoggingHook`

Расширенный хук со статистикой.

**Инициализация:**
```python
>>> from src.repository.monitoring import DetailedLoggingHook
>>>
>>> hook = DetailedLoggingHook(
...     slow_query_threshold_ms=200,
...     log_query_params=True  # По умолчанию True
... )
>>>
>>> repo.add_hook(hook)
```

**Дополнительные возможности:**
- Подсчёт общего количества запросов
- Среднее время выполнения
- Cache hit rate (процент попаданий в кеш)
- Статистика каждые 10 запросов

**Пример логов:**
```
INFO: Query 'select' for ProductModel: 45.2ms, 150 rows | Params: {'is_active': True}
INFO: Query stats: count=10, avg_time=52.3ms, cache_hit_rate=30.0%
INFO: Query 'select' for ProductModel: 15.1ms, 50 rows | Params: {'category_id': UUID(...)}
```

---

## 🔧 Управление Hooks

### Добавление hooks

```python
>>> from src.repository.monitoring import LoggingHook, DetailedLoggingHook
>>>
>>> # Можно добавить несколько hooks
>>> repo.add_hook(LoggingHook(slow_query_threshold_ms=100))
>>> repo.add_hook(DetailedLoggingHook())
>>> repo.add_hook(CustomMetricsHook())  # Ваш custom hook
>>>
>>> # Все hooks будут вызваны для каждого запроса
```

### Удаление hooks

```python
>>> hook = LoggingHook()
>>> repo.add_hook(hook)
>>>
>>> # Удалить конкретный hook
>>> repo.remove_hook(hook)
>>>
>>> # Очистить все hooks
>>> repo.hooks.clear()
```

---

## 📈 QueryMetrics

Структура данных с метриками выполнения запроса.

**Поля:**
```python
@dataclass
class QueryMetrics:
    query_type: str              # "select", "insert", "update", "delete"
    model_name: str              # "ProductModel"
    execution_time_ms: float     # 45.2
    rows_affected: int           # 150
    timestamp: datetime          # datetime.now()
    query_params: Dict[str, Any] # {"is_active": True, "limit": 10}
    cache_hit: bool              # False
    error: Optional[str]         # None или текст ошибки
```

---

## 🎨 Создание Custom Hook

Создайте свой hook для интеграции с системами мониторинга.

### Базовый пример

```python
>>> from src.repository.monitoring import QueryHook, QueryMetrics
>>>
>>> class PrometheusHook(QueryHook):
...     """Отправка метрик в Prometheus."""
...
...     def __init__(self, prometheus_client):
...         self.client = prometheus_client
...         self.query_counter = Counter('db_queries_total', 'Total queries')
...         self.query_duration = Histogram('db_query_duration_ms', 'Query duration')
...
...     async def before_execute(self, query_type, model_name, query_params=None):
...         # Можно логировать начало запроса
...         pass
...
...     async def after_execute(self, metrics: QueryMetrics):
...         # Отправить метрики в Prometheus
...         self.query_counter.inc()
...         self.query_duration.observe(metrics.execution_time_ms)
>>>
>>> # Использование
>>> prom_hook = PrometheusHook(prometheus_client)
>>> repo.add_hook(prom_hook)
```

### Продвинутый пример - Sentry

```python
>>> import sentry_sdk
>>> from src.repository.monitoring import QueryHook, QueryMetrics
>>>
>>> class SentryHook(QueryHook):
...     """Отправка медленных запросов в Sentry."""
...
...     def __init__(self, slow_threshold_ms=1000):
...         self.slow_threshold_ms = slow_threshold_ms
...
...     async def before_execute(self, query_type, model_name, query_params=None):
...         pass
...
...     async def after_execute(self, metrics: QueryMetrics):
...         # Если запрос слишком медленный или ошибка - отправить в Sentry
...         if metrics.error:
...             sentry_sdk.capture_message(
...                 f"DB Error: {metrics.error}",
...                 level="error",
...                 extra={
...                     "query_type": metrics.query_type,
...                     "model": metrics.model_name,
...                     "duration_ms": metrics.execution_time_ms
...                 }
...             )
...         elif metrics.execution_time_ms > self.slow_threshold_ms:
...             sentry_sdk.capture_message(
...                 f"Slow Query: {metrics.model_name}.{metrics.query_type}",
...                 level="warning",
...                 extra={
...                     "duration_ms": metrics.execution_time_ms,
...                     "rows": metrics.rows_affected,
...                     "params": metrics.query_params
...                 }
...             )
>>>
>>> # Использование
>>> sentry_hook = SentryHook(slow_threshold_ms=500)
>>> repo.add_hook(sentry_hook)
```

### Custom metrics aggregation

```python
>>> class MetricsAggregatorHook(QueryHook):
...     """Агрегация метрик для аналитики."""
...
...     def __init__(self):
...         self.metrics_by_model = defaultdict(list)
...
...     async def before_execute(self, query_type, model_name, query_params=None):
...         pass
...
...     async def after_execute(self, metrics: QueryMetrics):
...         self.metrics_by_model[metrics.model_name].append({
...             'type': metrics.query_type,
...             'duration': metrics.execution_time_ms,
...             'rows': metrics.rows_affected,
...             'cached': metrics.cache_hit
...         })
...
...     def get_stats(self, model_name: str):
...         """Получить статистику по модели."""
...         metrics = self.metrics_by_model[model_name]
...
...         return {
...             'total_queries': len(metrics),
...             'avg_duration': sum(m['duration'] for m in metrics) / len(metrics),
...             'total_rows': sum(m['rows'] for m in metrics),
...             'cache_hit_rate': sum(1 for m in metrics if m['cached']) / len(metrics) * 100
...         }
>>>
>>> # Использование
>>> aggregator = MetricsAggregatorHook()
>>> repo.add_hook(aggregator)
>>>
>>> # ... выполнить операции
>>>
>>> # Получить статистику
>>> stats = aggregator.get_stats('ProductModel')
>>> print(f"Avg query time: {stats['avg_duration']:.2f}ms")
>>> print(f"Cache hit rate: {stats['cache_hit_rate']:.1f}%")
```

---

## 🔍 Примеры использования

### Development: детальное логирование

```python
>>> from src.repository.monitoring import DetailedLoggingHook
>>>
>>> # Включить детальное логирование для отладки
>>> repo = ProductRepository(session, ProductModel)
>>> repo.add_hook(DetailedLoggingHook(
...     slow_query_threshold_ms=50,  # Низкий порог для dev
...     log_query_params=True  # Видеть все параметры
... ))
>>>
>>> # Все запросы логируются с параметрами
>>> products = await repo.filter_by(
...     is_active=True,
...     price__gte=1000,
...     limit=10
... )
>>> # INFO: Query 'select' for ProductModel: 25.3ms, 10 rows |
>>> #       Params: {'is_active': True, 'price__gte': 1000, 'limit': 10}
```

### Production: мониторинг медленных запросов

```python
>>> # Только медленные запросы и ошибки
>>> repo = ProductRepository(session, ProductModel)
>>> repo.add_hook(LoggingHook(
...     slow_query_threshold_ms=200,  # Высокий порог для prod
...     log_query_params=False  # Не логировать параметры (безопасность)
... ))
>>>
>>> # Логируются только запросы > 200ms
>>> products = await repo.filter_by(is_active=True, limit=10000)
>>> # WARNING: SLOW Query 'select' for ProductModel: 350.2ms, 10000 rows
```

### Комбинирование hooks

```python
>>> # Несколько hooks одновременно
>>> repo = ProductRepository(session, ProductModel)
>>>
>>> # 1. Логирование
>>> repo.add_hook(LoggingHook())
>>>
>>> # 2. Метрики в Prometheus
>>> repo.add_hook(PrometheusHook(prom_client))
>>>
>>> # 3. Алерты в Sentry
>>> repo.add_hook(SentryHook(slow_threshold_ms=1000))
>>>
>>> # 4. Агрегация для дашборда
>>> repo.add_hook(MetricsAggregatorHook())
>>>
>>> # Все 4 hooks выполняются для каждого запроса
```

---

## ⚡ Performance Impact

**Overhead от hooks:**
- `LoggingHook`: ~0.1-0.5ms на запрос
- `DetailedLoggingHook`: ~0.2-1ms на запрос
- Custom hooks: зависит от реализации

**Рекомендации:**
- В production используйте hooks с минимальным overhead
- Избегайте сложной логики в `before_execute` и `after_execute`
- Async операции выполняйте в фоне (не блокируйте запрос)

---

## Следующий раздел

- [**BEST_PRACTICES.md**](./BEST_PRACTICES.md) - Лучшие практики и оптимизация
