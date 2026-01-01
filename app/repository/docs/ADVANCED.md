# Advanced Features

Продвинутые возможности BaseRepository: SELECT FOR UPDATE, проекции, кеширование и batch операции.

## 🔒 SELECT FOR UPDATE (Pessimistic Locking)

Блокировка записей для конкурентных операций.

### `get_item_by_id_for_update()`

Получить запись по ID с блокировкой.

**Сигнатура:**
```python
async def get_item_by_id_for_update(
    item_id: UUID,
    nowait: bool = False,
    skip_locked: bool = False,
    options: Optional[List[Any]] = None
) -> Optional[M]
```

**Параметры:**
- `item_id` - UUID записи
- `nowait` - не ждать если заблокирована (вызвать ошибку сразу)
- `skip_locked` - пропустить заблокированные записи
- `options` - опции загрузки relationships

**Возвращает:** Модель или `None`

**Когда использовать:**
- Обновление количества товара при заказе
- Изменение баланса счёта
- Любые критические операции read-modify-write

**Примеры:**
```python
>>> # Уменьшение количества товара
>>> product = await repo.get_item_by_id_for_update(product_id)
>>> if product.quantity >= order_quantity:
...     product.quantity -= order_quantity
...     await session.commit()  # Блокировка снимается
... else:
...     raise InsufficientStockError()
>>>
>>> # С nowait: ошибка если заблокировано
>>> try:
...     product = await repo.get_item_by_id_for_update(
...         product_id,
...         nowait=True
...     )
... except OperationalError:
...     raise ResourceLockedError("Товар уже обрабатывается")
>>>
>>> # С skip_locked: пропустить заблокированные
>>> product = await repo.get_item_by_id_for_update(
...     product_id,
...     skip_locked=True
... )
>>> if product is None:
...     # Запись заблокирована или не существует
...     return None
```

**⚠️ Важно:**
- Блокировка активна до конца транзакции (commit/rollback)
- Всегда используйте в контексте транзакции
- Возможна deadlock ситуация - обрабатывайте исключения

---

### `filter_by_for_update()`

Фильтрация с блокировкой нескольких записей.

**Сигнатура:**
```python
async def filter_by_for_update(
    nowait: bool = False,
    skip_locked: bool = False,
    options: Optional[List[Any]] = None,
    **filters
) -> List[M]
```

**Параметры:**
- `nowait` - не ждать если записи заблокированы
- `skip_locked` - пропустить заблокированные
- `options` - опции загрузки
- `**filters` - фильтры (как в `filter_by`)

**Возвращает:** Список заблокированных моделей

**Примеры:**
```python
>>> # Заблокировать все заказы "в обработке"
>>> orders = await repo.filter_by_for_update(
...     status="processing"
... )
>>> for order in orders:
...     order.status = "completed"
...     order.completed_at = datetime.now()
>>> await session.commit()
>>>
>>> # С skip_locked: обработать только свободные
>>> orders = await repo.filter_by_for_update(
...     status="pending",
...     skip_locked=True,
...     limit=10
... )
>>> # Обработка только незаблокированных заказов
>>> for order in orders:
...     process_order(order)
```

---

## 🎯 Projections (Частичная загрузка)

Загрузка только нужных полей вместо полных моделей.

### `project_fields()`

Получить несколько полей как список словарей.

**Сигнатура:**
```python
async def project_fields(
    fields: List[str],
    **filters
) -> List[Dict[str, Any]]
```

**Параметры:**
- `fields` - список названий полей
- `**filters` - фильтры (поддерживает операторы)

**Возвращает:** Список словарей `{поле: значение}`

**Преимущества:**
- Экономия памяти (не загружается вся модель)
- Быстрее выполнение (меньше данных)
- Удобно для API (сразу JSON-ready)

**Примеры:**
```python
>>> # Список продуктов для dropdown
>>> products = await repo.project_fields(
...     ['id', 'name'],
...     is_active=True
... )
>>> # [{"id": UUID(...), "name": "Молоток"}, ...]
>>>
>>> # Для отчёта
>>> report = await repo.project_fields(
...     ['name', 'price', 'quantity'],
...     category_id=category_id,
...     is_active=True
... )
>>> # [{"name": "...", "price": 500, "quantity": 10}, ...]
>>>
>>> # С фильтрацией
>>> expensive = await repo.project_fields(
...     ['id', 'name', 'price'],
...     price__gte=5000,
...     limit=100
... )
```

**Сравнение производительности:**
```python
# ❌ Плохо: загрузка полных моделей
products = await repo.filter_by(is_active=True)
names = [p.name for p in products]  # Загружено всё, используется только name

# ✅ Хорошо: только нужное поле
names = await repo.project_field('name', is_active=True)
```

---

### `project_field()`

Получить одно поле как список значений.

**Сигнатура:**
```python
async def project_field(
    field_name: str,
    **filters
) -> List[Any]
```

**Параметры:**
- `field_name` - название поля
- `**filters` - фильтры

**Возвращает:** Список значений поля

**Примеры:**
```python
>>> # Список всех кодов категорий
>>> codes = await repo.project_field('code')
>>> # ["tools", "electric", "building", ...]
>>>
>>> # IDs активных продуктов
>>> product_ids = await repo.project_field('id', is_active=True)
>>> # [UUID(...), UUID(...), ...]
>>>
>>> # Emails пользователей с ролью admin
>>> admin_emails = await repo.project_field(
...     'email',
...     role='admin',
...     is_active=True
... )
>>>
>>> # Использование для bulk операций
>>> category_ids = await repo.project_field('id', parent_id__is_null=True)
>>> await product_repo.bulk_update_field('category_id', None, id__in=category_ids)
```

---

### `project_one()`

Получить одну запись с проекцией.

**Сигнатура:**
```python
async def project_one(
    fields: List[str],
    **filters
) -> Optional[Dict[str, Any]]
```

**Параметры:**
- `fields` - список полей
- `**filters` - фильтры

**Возвращает:** Словарь или `None`

**Примеры:**
```python
>>> # Получить название и код категории
>>> category = await repo.project_one(
...     ['name', 'code'],
...     id=category_id
... )
>>> # {"name": "Инструменты", "code": "tools"}
>>>
>>> # Для проверки существования с данными
>>> product = await repo.project_one(
...     ['id', 'name', 'price'],
...     sku="P-12345"
... )
>>> if product:
...     print(f"{product['name']}: ${product['price']}")
```

---

## 💾 Caching (Кеширование)

Опциональное кеширование для read-only запросов.

### Настройка кеша

**Реализации:**
- `RedisCacheBackend` - production (переиспользует существующий Redis)
- `InMemoryCacheBackend` - development/testing
- `NoCacheBackend` - кеш отключен (по умолчанию)

**Инициализация:**
```python
>>> from src.repository.cache import RedisCacheBackend, InMemoryCacheBackend
>>>
>>> # Production: Redis
>>> cache = RedisCacheBackend()
>>> repo = ProductRepository(session, ProductModel, cache_backend=cache)
>>>
>>> # Development: In-memory
>>> cache = InMemoryCacheBackend()
>>> repo = ProductRepository(session, ProductModel, cache_backend=cache)
>>>
>>> # Без кеша (по умолчанию)
>>> repo = ProductRepository(session, ProductModel)
```

---

### `get_item_by_id_cached()`

Получение с кешированием.

**Сигнатура:**
```python
async def get_item_by_id_cached(
    item_id: UUID,
    use_cache: bool = True,
    cache_ttl: int = 300,
    options: Optional[List[Any]] = None
) -> Optional[M]
```

**Параметры:**
- `item_id` - UUID записи
- `use_cache` - использовать ли кеш
- `cache_ttl` - время жизни в секундах (по умолчанию 300 = 5 минут)
- `options` - опции загрузки

**Возвращает:** Модель или `None`

**Примеры:**
```python
>>> # С кешированием на 5 минут (по умолчанию)
>>> product = await repo.get_item_by_id_cached(product_id)
>>>
>>> # С кешированием на 10 минут
>>> category = await repo.get_item_by_id_cached(
...     category_id,
...     cache_ttl=600
... )
>>>
>>> # Без кеша (bypass)
>>> product = await repo.get_item_by_id_cached(
...     product_id,
...     use_cache=False
... )
>>>
>>> # С загрузкой relationships
>>> product = await repo.get_item_by_id_cached(
...     product_id,
...     cache_ttl=300,
...     options=[selectinload(ProductModel.category)]
... )
```

**Автоматическая инвалидация:**
```python
>>> # Кеш автоматически инвалидируется при:
>>>
>>> # 1. Обновлении
>>> await repo.update_item(product_id, {"price": 1500})
>>> # Кеш для product_id очищен
>>>
>>> # 2. Bulk upsert
>>> await repo.bulk_upsert(items, conflict_columns=['code'])
>>> # Весь кеш модели очищен
>>>
>>> # 3. Удалении
>>> await repo.delete_item(product_id)
>>> # Кеш для product_id очищен
```

**Ключи кеша:**
```
Формат: {ModelName}:{operation}:{args}
Примеры:
- ProductModel:get_by_id:123e4567-e89b-12d3-a456-426614174000
- CategoryModel:get_by_id:7c9e6679-7425-40de-944b-e07fc1f90ae7
```

---

## 🔢 Batch Operations

Массовые операции для оптимизации производительности.

### `bulk_create()`

См. [CRUD.md](./CRUD.md#bulk_create)

---

### `bulk_update()`

Массовое обновление моделей.

**Сигнатура:**
```python
async def bulk_update(
    models: List[M]
) -> None
```

**Параметры:**
- `models` - список моделей SQLAlchemy с изменениями

**Пример:**
```python
>>> # Получить продукты
>>> products = await repo.filter_by(category_id=old_cat_id)
>>>
>>> # Изменить
>>> for product in products:
...     product.category_id = new_cat_id
...     product.updated_at = datetime.now()
>>>
>>> # Сохранить все за раз
>>> await repo.bulk_update(products)
```

---

### `bulk_upsert()`

См. [CRUD.md](./CRUD.md#bulk_upsert)

**Дополнительный пример - синхронизация с внешним API:**
```python
>>> # Получить данные из внешнего API
>>> external_products = await fetch_from_external_api()
>>>
>>> # Преобразовать в формат БД
>>> items = []
>>> for ext_product in external_products:
...     items.append({
...         "external_id": ext_product.id,
...         "name": ext_product.name,
...         "price": ext_product.price,
...         "updated_at": datetime.now()
...     })
>>>
>>> # Upsert: обновить существующие, создать новые
>>> count = await repo.bulk_upsert(
...     items,
...     conflict_columns=['external_id'],
...     update_columns=['name', 'price', 'updated_at']
... )
>>>
>>> print(f"Синхронизировано {count} товаров")
```

---

## 📊 Сравнение производительности

### Проекции vs Полные модели

```python
# Задача: получить 1000 названий продуктов

# ❌ МЕДЛЕННО: Полные модели
products = await repo.get_items(limit=1000)
names = [p.name for p in products]
# ~200ms, ~500KB памяти

# ✅ БЫСТРО: Проекция
names = await repo.project_field('name', limit=1000)
# ~50ms, ~50KB памяти

# Выигрыш: 4x быстрее, 10x меньше памяти
```

### Batch vs Индивидуальные операции

```python
# Задача: создать 100 продуктов

# ❌ МЕДЛЕННО: По одному
for item in items:
    await repo.create_item(item)
# ~1000ms (100 запросов)

# ✅ БЫСТРО: Batch
await repo.bulk_create(items)
# ~50ms (1 запрос)

# Выигрыш: 20x быстрее
```

### Кеширование

```python
# Задача: 100 запросов одного продукта

# ❌ БЕЗ КЕША
for _ in range(100):
    product = await repo.get_item_by_id(product_id)
# ~500ms (100 запросов к БД)

# ✅ С КЕШЕМ
for _ in range(100):
    product = await repo.get_item_by_id_cached(product_id)
# ~10ms (1 запрос к БД + 99 из кеша)

# Выигрыш: 50x быстрее
```

---

## Следующие разделы

- [**MONITORING.md**](./MONITORING.md) - Трассировка и мониторинг
- [**BEST_PRACTICES.md**](./BEST_PRACTICES.md) - Лучшие практики
