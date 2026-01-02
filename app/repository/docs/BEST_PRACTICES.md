# Best Practices

Лучшие практики работы с BaseRepository для оптимальной производительности и чистого кода.

## 🎯 Основные принципы

### 1. Используйте проекции для списков

**❌ Плохо:**
```python
# Загружаем полные модели, используем только name
products = await repo.get_items()
names = [p.name for p in products]
```

**✅ Хорошо:**
```python
# Загружаем только name
names = await repo.project_field('name')
```

**Выигрыш:** 5-10x быстрее, значительно меньше памяти

---

### 2. Настройте default_options

Избегайте N+1 проблемы через default_options.

**❌ Плохо:**
```python
class ProductRepository(BaseRepository[ProductModel]):
    pass

# N+1: 1 запрос products + N запросов categories
products = await repo.get_items()
for product in products:
    print(product.category.name)  # Каждый раз новый запрос!
```

**✅ Хорошо:**
```python
from sqlalchemy.orm import selectinload

class ProductRepository(BaseRepository[ProductModel]):
    default_options = [
        selectinload(ProductModel.category),
        selectinload(ProductModel.images)
    ]

# 1 запрос products + 1 запрос categories (joinedload = 1 запрос total)
products = await repo.get_items()
for product in products:
    print(product.category.name)  # Уже загружено!
```

---

### 3. Используйте batch операции

**❌ Плохо:**
```python
# N запросов
for item_data in items:
    await repo.create_item(item_data)
```

**✅ Хорошо:**
```python
# 1 запрос
await repo.bulk_create(items)
```

---

### 4. SELECT FOR UPDATE для конкурентных операций

**❌ Плохо (race condition):**
```python
# Два параллельных запроса могут создать отрицательный остаток!
product = await repo.get_item_by_id(product_id)
product.quantity -= order_quantity
await session.commit()
```

**✅ Хорошо:**
```python
# Блокировка гарантирует атомарность
product = await repo.get_item_by_id_for_update(product_id)
if product.quantity >= order_quantity:
    product.quantity -= order_quantity
    await session.commit()
else:
    raise InsufficientStockError()
```

---

### 5. Кеширование для read-heavy операций

**Когда использовать:**
- Справочники (категории, теги, настройки)
- Данные которые редко меняются
- Высокая частота чтения

**❌ Плохо:**
```python
# Каждый раз запрос к БД
categories = await repo.filter_by(is_active=True)
```

**✅ Хорошо:**
```python
# Production
cache = RedisCacheBackend()
repo = CategoryRepository(session, CategoryModel, cache_backend=cache)

# Первый запрос - к БД, остальные - из кеша
categories = await repo.get_items()
```

---

## 🚀 Оптимизация производительности

### Выбор операторов загрузки relationships

**selectinload** - отдельный запрос (IN query)
```python
default_options = [selectinload(ProductModel.categories)]
# SELECT * FROM products
# SELECT * FROM categories WHERE id IN (...)
```

**Когда использовать:**
- Relationship с многими записями (много categories на product)
- Когда не все records используют relationship
- По умолчанию рекомендуется

**joinedload** - JOIN в одном запросе
```python
default_options = [joinedload(ProductModel.category)]
# SELECT * FROM products LEFT JOIN categories ON ...
```

**Когда использовать:**
- One-to-one или many-to-one relationships
- Всегда нужен relationship
- Меньше запросов > меньше данных

**Пример:**
```python
class ProductRepository(BaseRepository[ProductModel]):
    default_options = [
        joinedload(ProductModel.category),      # Many-to-one: 1 запрос
        selectinload(ProductModel.images),      # One-to-many: +1 запрос
        selectinload(ProductModel.tags)         # Many-to-many: +1 запрос
    ]
# Итого: 3 запроса вместо потенциальных 1+N+M+K
```

---

### Пагинация больших списков

**❌ Плохо:**
```python
# Загрузить все 10000 записей в память
products = await repo.get_items()
```

**✅ Хорошо:**
```python
# Порциями по 100
page_size = 100
offset = 0

while True:
    products = await repo.get_items(limit=page_size, offset=offset)
    if not products:
        break

    process_products(products)
    offset += page_size
```

**✅ Ещё лучше:**
```python
# Используйте встроенную пагинацию
from app.schemas.v1.pagination import PaginationParams

pagination = PaginationParams(page=1, page_size=100, sort_by="created_at")
products, total = await repo.get_paginated_items(pagination)
```

---

### Фильтрация vs Python filter

**❌ Плохо:**
```python
# Загружаем все, фильтруем в Python
all_products = await repo.get_items()
active_products = [p for p in all_products if p.is_active]
```

**✅ Хорошо:**
```python
# Фильтруем на уровне БД
active_products = await repo.filter_by(is_active=True)
```

---

## 📐 Паттерны проектирования

### Repository per Model

Создайте отдельный репозиторий для каждой модели.

```python
class ProductRepository(BaseRepository[ProductModel]):
    default_options = [
        selectinload(ProductModel.category),
        selectinload(ProductModel.images)
    ]

    async def get_bestsellers(self, limit: int = 10):
        """Кастомный метод для бизнес-логики."""
        return await self.filter_by_ordered(
            "sales_count",
            ascending=False,
            is_active=True,
            limit=limit
        )

class CategoryRepository(BaseRepository[CategoryModel]):
    default_options = [selectinload(CategoryModel.children)]

    async def get_tree(self):
        """Получить дерево категорий."""
        root_categories = await self.filter_by(parent_id__is_null=True)
        # ... build tree logic
        return root_categories
```

---

### Service Layer Pattern

Используйте репозитории через service layer.

```python
class ProductService:
    def __init__(self, session: AsyncSession):
        self.product_repo = ProductRepository(session, ProductModel)
        self.category_repo = CategoryRepository(session, CategoryModel)

    async def create_product_with_category(
        self,
        product_data: dict,
        category_code: str
    ):
        # Найти или создать категорию
        category, _ = await self.category_repo.get_or_create(
            filters={"code": category_code},
            defaults={"name": category_code.title(), "is_active": True}
        )

        # Создать продукт
        product_data["category_id"] = category.id
        product = await self.product_repo.create_item(product_data)

        return product
```

---

### Dependency Injection

Используйте FastAPI dependencies.

```python
# В dependencies.py
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.repository.cache import RedisCacheBackend

async def get_product_repo(
    session: AsyncSession = Depends(get_session)
) -> ProductRepository:
    cache = RedisCacheBackend()
    return ProductRepository(
        session,
        ProductModel,
        cache_backend=cache,
        enable_tracing=settings.DEBUG
    )

# В роутере
@router.get("/products/")
async def get_products(
    repo: ProductRepository = Depends(get_product_repo)
):
    products = await repo.filter_by(is_active=True)
    return products
```

---

## ⚠️ Частые ошибки

### 1. Забыть про commit

**❌ Ошибка:**
```python
await repo.create_item(data, commit=False)
# Забыли вызвать session.commit()
# Изменения не сохранены!
```

**✅ Правильно:**
```python
await repo.create_item(data, commit=False)
await repo.update_item(id, other_data, commit=False)
await session.commit()  # Сохранить все изменения
```

---

### 2. N+1 запросов

**❌ Ошибка:**
```python
products = await repo.get_items()
for product in products:
    # Каждая итерация = новый запрос!
    category_name = product.category.name
```

**✅ Правильно:**
```python
products = await repo.get_items(
    options=[selectinload(ProductModel.category)]
)
for product in products:
    category_name = product.category.name  # Уже загружено
```

---

### 3. Не использовать проекции для больших списков

**❌ Ошибка:**
```python
# Загружаем 10000 полных моделей для dropdown
products = await repo.get_items()
dropdown_data = [{"id": p.id, "name": p.name} for p in products]
```

**✅ Правильно:**
```python
# Загружаем только нужные поля
dropdown_data = await repo.project_fields(['id', 'name'])
```

---

### 4. Race conditions без блокировок

**❌ Ошибка:**
```python
# Два параллельных запроса создадут duplicate
existing = await repo.get_item_by_field("email", email)
if not existing:
    user = await repo.create_item({"email": email, ...})
```

**✅ Правильно (вариант 1):**
```python
# Использовать unique constraint + обработку ошибок
try:
    user = await repo.create_item({"email": email, ...})
except IntegrityError:
    user = await repo.get_item_by_field("email", email)
```

**✅ Правильно (вариант 2):**
```python
# Использовать get_or_create
user, created = await repo.get_or_create(
    filters={"email": email},
    defaults={"name": name, "is_active": True}
)
```

---

## 📊 Cheatsheet

### Когда что использовать

| Задача | Метод | Причина |
|--------|-------|---------|
| Получить по ID | `get_item_by_id()` | Простейший случай |
| Список для dropdown | `project_fields(['id', 'name'])` | Меньше данных |
| Только IDs | `project_field('id')` | Минимум данных |
| Фильтрация | `filter_by(**filters)` | Гибкая фильтрация |
| Массовое создание | `bulk_create()` | Один запрос |
| Upsert | `bulk_upsert()` | Создать или обновить |
| Конкурентное обновление | `get_item_by_id_for_update()` | Избежать race condition |
| Справочники | `get_item_by_id_cached()` | Кеширование |
| Счётчик | `count_items()` | Эффективнее чем len() |
| Проверка существования | `exists_by_field()` | Не загружает данные |

---

## 🎓 Резюме

1. **Проекции** вместо полных моделей для списков
2. **default_options** для избежания N+1
3. **Batch операции** для массовых изменений
4. **SELECT FOR UPDATE** для критических операций
5. **Кеширование** для read-heavy данных
6. **Пагинация** для больших списков
7. **Service Layer** для бизнес-логики
8. **Dependency Injection** для чистоты кода
