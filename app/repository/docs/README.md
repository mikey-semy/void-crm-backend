# BaseRepository - Обзор

Базовый репозиторий предоставляет полный набор методов для работы с базой данных с автоматической оптимизацией и минимизацией запросов.

## Возможности

### 🎯 Основные
- **CRUD операции** - полный набор методов создания, чтения, обновления и удаления
- **Фильтрация** - мощная система фильтров с операторами (eq, ne, gt, lt, gte, lte, in, not_in, like, ilike, is_null)
- **Пагинация** - встроенная поддержка пагинации с сортировкой
- **Relationships** - автоматическая загрузка связанных объектов

### ⚡ Оптимизация
- **Проекции** - загрузка только нужных полей (экономия памяти)
- **Кеширование** - опциональное кеширование read-only запросов
- **Batch операции** - массовые insert/update/upsert
- **Default options** - автоматическая загрузка relationships

### 🔒 Конкурентность
- **SELECT FOR UPDATE** - pessimistic locking для критических операций
- **skip_locked** и **nowait** режимы

### 📊 Мониторинг
- **Query hooks** - система хуков для трассировки
- **Метрики** - автоматический сбор времени выполнения и количества строк
- **Логирование** - встроенное логирование медленных запросов

## Быстрый старт

### 1. Создание репозитория

```python
from app.repository.v1.base import BaseRepository
from app.models.v1 import ProductModel
from sqlalchemy.orm import selectinload

class ProductRepository(BaseRepository[ProductModel]):
    # Опционально: задайте default options для автозагрузки relationships
    default_options = [
        selectinload(ProductModel.categories),
        selectinload(ProductModel.images)
    ]
```

### 2. Использование в сервисах

```python
from sqlalchemy.ext.asyncio import AsyncSession

class ProductService:
    def __init__(self, session: AsyncSession):
        self.repo = ProductRepository(session, ProductModel)

    async def get_active_products(self):
        # Все активные продукты с автозагрузкой categories и images
        return await self.repo.filter_by(is_active=True)

    async def get_product_names(self):
        # Только имена (без загрузки полных моделей)
        return await self.repo.project_field('name', is_active=True)
```

### 3. С кешированием и трассировкой

```python
from app.repository.cache import RedisCacheBackend

# В dependency
async def get_product_repo(session: AsyncSession):
    cache = RedisCacheBackend()
    return ProductRepository(
        session,
        ProductModel,
        cache_backend=cache,
        enable_tracing=True  # Логирование метрик
    )
```

## Архитектура

```
BaseRepository
├── SessionMixin         # Управление сессией
├── Cache Integration    # Опциональное кеширование
├── Query Hooks          # Система трассировки
└── Methods
    ├── CRUD             # create, read, update, delete
    ├── Filtering        # filter_by, count, exists
    ├── Projections      # project_fields, project_field
    ├── Locking          # *_for_update методы
    ├── Batch            # bulk_create, bulk_update, bulk_upsert
    └── Utilities        # get_or_create, update_or_create
```

## Примеры использования

### Простой CRUD

```python
# Создание
product = await repo.create_item({
    "name": "Молоток",
    "price": 500,
    "is_active": True
})

# Чтение
product = await repo.get_item_by_id(product_id)
products = await repo.filter_by(is_active=True, limit=10)

# Обновление
await repo.update_item(product_id, {"price": 600})

# Удаление
await repo.delete_item(product_id)
```

### Фильтрация с операторами

```python
# Цена >= 1000
expensive = await repo.filter_by(price__gte=1000)

# Имя содержит "молот" (case-insensitive)
hammers = await repo.filter_by(name__ilike="%молот%")

# Категория в списке
items = await repo.filter_by(category_id__in=[cat1_id, cat2_id])

# Без родителя
root_categories = await repo.filter_by(parent_id__is_null=True)
```

### Оптимизация запросов

```python
# Вместо полных моделей - только нужные поля
products = await repo.project_fields(
    ['id', 'name', 'price'],
    is_active=True,
    limit=100
)
# Результат: [{"id": ..., "name": "...", "price": 500}, ...]

# Только список IDs
ids = await repo.project_field('id', is_active=True)
# Результат: [UUID(...), UUID(...), ...]
```

### Конкурентные операции

```python
# Уменьшение количества товара с блокировкой
product = await repo.get_item_by_id_for_update(product_id)
if product.quantity >= order_quantity:
    product.quantity -= order_quantity
    await session.commit()  # Блокировка снимается
else:
    raise InsufficientStock()
```

### Batch операции

```python
# Массовое создание
products = await repo.bulk_create([
    {"name": "Товар 1", "price": 100},
    {"name": "Товар 2", "price": 200},
    {"name": "Товар 3", "price": 300},
])

# Upsert (создать или обновить)
await repo.bulk_upsert(
    [
        {"code": "A001", "name": "Новое название", "price": 150},
        {"code": "A002", "name": "Товар 2", "price": 250},
    ],
    conflict_columns=['code'],  # Конфликт по code
    update_columns=['name', 'price']  # Обновить эти поля
)
```

## Следующие шаги

- [**CRUD.md**](./CRUD.md) - Детальное описание CRUD операций
- [**FILTERING.md**](./FILTERING.md) - Все операторы фильтрации
- [**ADVANCED.md**](./ADVANCED.md) - Продвинутые возможности
- [**MONITORING.md**](./MONITORING.md) - Настройка мониторинга
- [**BEST_PRACTICES.md**](./BEST_PRACTICES.md) - Лучшие практики
