# BaseRepository Documentation

Полная документация базового репозитория с расширенной функциональностью для работы с базой данных.

## 📚 Содержание

1. [**README.md**](./README.md) - Обзор и быстрый старт
2. [**CRUD.md**](./CRUD.md) - CRUD операции (Create, Read, Update, Delete)
3. [**FILTERING.md**](./FILTERING.md) - Фильтрация и поиск
4. [**ADVANCED.md**](./ADVANCED.md) - Продвинутые возможности
   - SELECT FOR UPDATE
   - Проекции
   - Кеширование
   - Batch операции
5. [**MONITORING.md**](./MONITORING.md) - Трассировка и мониторинг
6. [**BEST_PRACTICES.md**](./BEST_PRACTICES.md) - Лучшие практики и оптимизация

## 🚀 Быстрый старт

```python
from app.repository.v1.base import BaseRepository
from app.models.v1 import ProductModel
from sqlalchemy.ext.asyncio import AsyncSession

# Создание репозитория
class ProductRepository(BaseRepository[ProductModel]):
    pass

# Использование
async def example(session: AsyncSession):
    repo = ProductRepository(session, ProductModel)

    # Получить все активные продукты
    products = await repo.filter_by(is_active=True)

    # Создать продукт
    product = await repo.create_item({
        "name": "Новый товар",
        "price": 1000,
        "is_active": True
    })
```

## 📖 Популярные методы

### Создание
- `create_item()` - создать одну запись
- `bulk_create()` - массовое создание
- `bulk_upsert()` - upsert с ON CONFLICT

### Чтение
- `get_item_by_id()` - получить по ID
- `filter_by()` - фильтрация с операторами
- `project_fields()` - частичная загрузка полей

### Обновление
- `update_item()` - обновить одну запись
- `bulk_update()` - массовое обновление

### Удаление
- `delete_item()` - удалить по ID
- `delete_by_filters()` - удалить по фильтрам

## 🔗 Навигация

Выберите нужный раздел из списка выше для детального изучения методов.
