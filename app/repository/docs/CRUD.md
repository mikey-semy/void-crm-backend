# CRUD Operations

Полный справочник CRUD операций (Create, Read, Update, Delete) в BaseRepository.

## 📝 Create (Создание)

### `create_item()`

Создание одной записи в базе данных.

**Сигнатура:**
```python
async def create_item(
    data: Dict[str, Any],
    commit: bool = True,
    options: Optional[List[Any]] = None,
    refresh: bool = True
) -> M
```

**Параметры:**
- `data` - словарь с данными для создания
- `commit` - делать ли commit сразу (по умолчанию `True`)
- `options` - опции загрузки relationships (selectinload, joinedload)
- `refresh` - обновить ли объект после создания (по умолчанию `True`)

**Возвращает:** Созданная SQLAlchemy модель

**Пример:**
```python
>>> # Создание продукта
>>> product = await repo.create_item({
...     "name": "Молоток",
...     "price": 500,
...     "is_active": True,
...     "category_id": category_id
... })
>>>
>>> # С автозагрузкой категории
>>> product = await repo.create_item(
...     {"name": "Дрель", "price": 3000},
...     options=[selectinload(ProductModel.category)]
... )
>>>
>>> # Без commit (для транзакций)
>>> product = await repo.create_item(
...     {"name": "Пила", "price": 1500},
...     commit=False
... )
>>> # ... другие операции
>>> await session.commit()
```

---

### `create_with_related()`

Создание записи со связанными объектами в одной транзакции.

**Сигнатура:**
```python
async def create_with_related(
    main_data: Dict[str, Any],
    related_items: List[Tuple[Type[BaseModel], Dict[str, Any]]]
) -> M
```

**Параметры:**
- `main_data` - данные для основной записи
- `related_items` - список кортежей `(МодельСвязки, данные)`

**Возвращает:** Созданная основная модель

**Пример:**
```python
>>> # Создать категорию с тегами
>>> category = await repo.create_with_related(
...     main_data={
...         "name": "Электроинструменты",
...         "code": "electric",
...         "is_active": True
...     },
...     related_items=[
...         (TagModel, {"name": "Популярное", "category_id": None}),
...         (TagModel, {"name": "Новинка", "category_id": None}),
...     ]
... )
```

**Особенности:**
- Атомарность: либо создаются ВСЕ записи, либо НИ ОДНА
- Автоматический rollback при ошибке
- `category_id` в related_items заполняется автоматически

---

### `bulk_create()`

Массовое создание записей.

**Сигнатура:**
```python
async def bulk_create(
    models: List[Union[M, Dict[str, Any]]],
    refresh: bool = True
) -> List[M]
```

**Параметры:**
- `models` - список моделей SQLAlchemy или словарей
- `refresh` - обновить ли модели после создания

**Возвращает:** Список созданных моделей

**Пример:**
```python
>>> # Создать несколько продуктов сразу
>>> products = await repo.bulk_create([
...     {"name": "Товар 1", "price": 100, "is_active": True},
...     {"name": "Товар 2", "price": 200, "is_active": True},
...     {"name": "Товар 3", "price": 300, "is_active": False},
... ])
>>>
>>> # Можно передать готовые модели
>>> models = [
...     ProductModel(name="Товар A", price=150),
...     ProductModel(name="Товар B", price=250),
... ]
>>> products = await repo.bulk_create(models)
```

**Преимущества:**
- Один запрос вместо N
- Значительно быстрее для больших объёмов
- Автоматический commit

---

### `bulk_upsert()`

Массовый upsert (создать или обновить) с PostgreSQL ON CONFLICT.

**Сигнатура:**
```python
async def bulk_upsert(
    items: List[Dict[str, Any]],
    conflict_columns: List[str],
    update_columns: Optional[List[str]] = None
) -> int
```

**Параметры:**
- `items` - список словарей с данными
- `conflict_columns` - поля для определения конфликта (unique keys)
- `update_columns` - поля для обновления при конфликте (по умолчанию все кроме conflict_columns)

**Возвращает:** Количество затронутых строк

**Пример:**
```python
>>> # Импорт категорий: обновить если code существует
>>> categories = [
...     {"code": "tools", "name": "Инструменты", "sort_order": 1},
...     {"code": "electric", "name": "Электрика", "sort_order": 2},
...     {"code": "build", "name": "Стройматериалы", "sort_order": 3},
... ]
>>>
>>> count = await repo.bulk_upsert(
...     categories,
...     conflict_columns=['code'],
...     update_columns=['name', 'sort_order']
... )
>>> print(f"Обработано {count} записей")
>>>
>>> # Обновление цен: если product_id существует
>>> price_updates = [
...     {"product_id": "uuid1", "price": 1200, "updated_at": datetime.now()},
...     {"product_id": "uuid2", "price": 1500, "updated_at": datetime.now()},
... ]
>>>
>>> await repo.bulk_upsert(
...     price_updates,
...     conflict_columns=['product_id']
...     # update_columns не указан - обновятся все поля
... )
```

**Преимущества:**
- Один запрос вместо множества SELECT + INSERT/UPDATE
- Атомарность всей операции
- Автоматическая инвалидация кеша

---

## 📖 Read (Чтение)

### `get_item_by_id()`

Получение записи по ID.

**Сигнатура:**
```python
async def get_item_by_id(
    item_id: UUID,
    options: Optional[List[Any]] = None
) -> Optional[M]
```

**Параметры:**
- `item_id` - UUID записи
- `options` - опции загрузки relationships

**Возвращает:** Модель или `None` если не найдена

**Пример:**
```python
>>> # Простое получение
>>> product = await repo.get_item_by_id(product_id)
>>>
>>> # С загрузкой категории
>>> product = await repo.get_item_by_id(
...     product_id,
...     options=[selectinload(ProductModel.category)]
... )
>>>
>>> # С загрузкой нескольких relationships
>>> product = await repo.get_item_by_id(
...     product_id,
...     options=[
...         selectinload(ProductModel.category),
...         selectinload(ProductModel.images),
...         selectinload(ProductModel.tags)
...     ]
... )
```

---

### `get_item_by_field()`

Получение одной записи по произвольному полю.

**Сигнатура:**
```python
async def get_item_by_field(
    field_name: str,
    field_value: Any,
    options: Optional[List[Any]] = None
) -> Optional[M]
```

**Параметры:**
- `field_name` - название поля
- `field_value` - значение для поиска
- `options` - опции загрузки relationships

**Возвращает:** Модель или `None`

**Пример:**
```python
>>> # Найти по коду
>>> category = await repo.get_item_by_field("code", "tools")
>>>
>>> # Найти по email
>>> user = await repo.get_item_by_field("email", "user@example.com")
>>>
>>> # С загрузкой связей
>>> product = await repo.get_item_by_field(
...     "sku",
...     "P-12345",
...     options=[selectinload(ProductModel.category)]
... )
```

---

### `get_items()`

Получение списка всех записей.

**Сигнатура:**
```python
async def get_items(
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    options: Optional[List[Any]] = None
) -> List[M]
```

**Параметры:**
- `limit` - максимальное количество записей
- `offset` - смещение (для пагинации)
- `options` - опции загрузки relationships

**Возвращает:** Список моделей

**Пример:**
```python
>>> # Все записи
>>> products = await repo.get_items()
>>>
>>> # Первые 10
>>> products = await repo.get_items(limit=10)
>>>
>>> # Пагинация: страница 2, по 20 записей
>>> page = 2
>>> page_size = 20
>>> products = await repo.get_items(
...     limit=page_size,
...     offset=(page - 1) * page_size
... )
>>>
>>> # С автозагрузкой категорий
>>> products = await repo.get_items(
...     limit=50,
...     options=[selectinload(ProductModel.category)]
... )
```

---

### `filter_by()`

Фильтрация записей с поддержкой операторов.

**Сигнатура:**
```python
async def filter_by(
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    options: Optional[List[Any]] = None,
    **filters
) -> List[M]
```

**Параметры:**
- `limit` - лимит записей
- `offset` - смещение
- `options` - опции загрузки
- `**filters` - фильтры в формате `field__operator=value`

**Возвращает:** Список моделей

**Операторы фильтрации:**
- `field=value` или `field__eq=value` - равно
- `field__ne=value` - не равно
- `field__gt=value` - больше
- `field__gte=value` - больше или равно
- `field__lt=value` - меньше
- `field__lte=value` - меньше или равно
- `field__in=[values]` - в списке
- `field__not_in=[values]` - не в списке
- `field__like=pattern` - LIKE (case-sensitive)
- `field__ilike=pattern` - LIKE (case-insensitive)
- `field__is_null=True/False` - IS NULL / IS NOT NULL

**Примеры:**
```python
>>> # Активные продукты
>>> products = await repo.filter_by(is_active=True)
>>>
>>> # Цена >= 1000
>>> expensive = await repo.filter_by(price__gte=1000)
>>>
>>> # Имя содержит "молот" (без учета регистра)
>>> hammers = await repo.filter_by(name__ilike="%молот%")
>>>
>>> # Категория в списке [cat1, cat2]
>>> products = await repo.filter_by(
...     category_id__in=[cat1_id, cat2_id],
...     is_active=True
... )
>>>
>>> # Комбинация фильтров
>>> products = await repo.filter_by(
...     is_active=True,
...     price__gte=100,
...     price__lte=1000,
...     category_id__ne=excluded_cat_id,
...     limit=20
... )
>>>
>>> # Без родителя (корневые категории)
>>> root_categories = await repo.filter_by(parent_id__is_null=True)
>>>
>>> # С родителем (не NULL)
>>> subcategories = await repo.filter_by(parent_id__is_null=False)
```

---

## ✏️ Update (Обновление)

### `update_item()`

Обновление одной записи по ID.

**Сигнатура:**
```python
async def update_item(
    item_id: UUID,
    data: Dict[str, Any],
    options: Optional[List[Any]] = None,
    refresh: bool = True
) -> Optional[M]
```

**Параметры:**
- `item_id` - UUID записи
- `data` - словарь с новыми значениями
- `options` - опции загрузки
- `refresh` - обновить ли объект после изменения

**Возвращает:** Обновлённая модель или `None`

**Пример:**
```python
>>> # Обновить цену
>>> product = await repo.update_item(
...     product_id,
...     {"price": 1200}
... )
>>>
>>> # Обновить несколько полей
>>> product = await repo.update_item(
...     product_id,
...     {
...         "name": "Новое название",
...         "price": 1500,
...         "is_active": False,
...         "updated_at": datetime.now()
...     }
... )
>>>
>>> # С загрузкой категории
>>> product = await repo.update_item(
...     product_id,
...     {"category_id": new_category_id},
...     options=[selectinload(ProductModel.category)]
... )
```

---

### `bulk_update()`

Массовое обновление записей.

**Сигнатура:**
```python
async def bulk_update(
    models: List[M]
) -> None
```

**Параметры:**
- `models` - список моделей SQLAlchemy для обновления

**Возвращает:** None

**Пример:**
```python
>>> # Получить продукты
>>> products = await repo.filter_by(category_id=old_category_id)
>>>
>>> # Изменить их
>>> for product in products:
...     product.category_id = new_category_id
...     product.updated_at = datetime.now()
>>>
>>> # Сохранить все изменения за раз
>>> await repo.bulk_update(products)
```

---

### `update_or_create()`

Обновить если существует, иначе создать.

**Сигнатура:**
```python
async def update_or_create(
    filters: Dict[str, Any],
    defaults: Dict[str, Any]
) -> Tuple[M, bool]
```

**Параметры:**
- `filters` - фильтры для поиска
- `defaults` - данные для создания/обновления

**Возвращает:** Кортеж `(модель, created)` где `created=True` если создана

**Пример:**
```python
>>> # Обновить настройку пользователя или создать
>>> setting, created = await repo.update_or_create(
...     filters={"user_id": user_id, "key": "theme"},
...     defaults={"value": "dark"}
... )
>>>
>>> if created:
...     print("Создана новая настройка")
... else:
...     print("Обновлена существующая настройка")
```

---

## 🗑️ Delete (Удаление)

### `delete_item()`

Удаление одной записи по ID.

**Сигнатура:**
```python
async def delete_item(
    item_id: UUID
) -> bool
```

**Параметры:**
- `item_id` - UUID записи

**Возвращает:** `True` если удалено, `False` если не найдено

**Пример:**
```python
>>> # Удалить продукт
>>> deleted = await repo.delete_item(product_id)
>>>
>>> if deleted:
...     print("Продукт удалён")
... else:
...     print("Продукт не найден")
```

---

### `delete_by_filters()`

Удаление записей по фильтрам.

**Сигнатура:**
```python
async def delete_by_filters(
    **filters
) -> int
```

**Параметры:**
- `**filters` - фильтры (те же что в `filter_by`)

**Возвращает:** Количество удалённых записей

**Пример:**
```python
>>> # Удалить все неактивные продукты
>>> count = await repo.delete_by_filters(is_active=False)
>>> print(f"Удалено {count} продуктов")
>>>
>>> # Удалить продукты категории
>>> count = await repo.delete_by_filters(category_id=category_id)
>>>
>>> # Удалить старые записи
>>> cutoff_date = datetime.now() - timedelta(days=90)
>>> count = await repo.delete_by_filters(created_at__lt=cutoff_date)
```

---

## 🔍 Утилиты

### `get_or_create()`

Получить запись или создать если не существует.

**Сигнатура:**
```python
async def get_or_create(
    filters: Dict[str, Any],
    defaults: Optional[Dict[str, Any]] = None
) -> Tuple[M, bool]
```

**Параметры:**
- `filters` - фильтры для поиска
- `defaults` - дополнительные данные для создания

**Возвращает:** Кортеж `(модель, created)`

**Пример:**
```python
>>> # Получить или создать категорию по коду
>>> category, created = await repo.get_or_create(
...     filters={"code": "tools"},
...     defaults={"name": "Инструменты", "is_active": True}
... )
>>>
>>> if created:
...     print("Создана новая категория")
... else:
...     print("Категория уже существует")
```

---

### `count_items()`

Подсчёт записей с фильтрами.

**Сигнатура:**
```python
async def count_items(
    **filters
) -> int
```

**Параметры:**
- `**filters` - фильтры (те же что в `filter_by`)

**Возвращает:** Количество записей

**Пример:**
```python
>>> # Всего продуктов
>>> total = await repo.count_items()
>>>
>>> # Активных продуктов
>>> active_count = await repo.count_items(is_active=True)
>>>
>>> # В категории
>>> cat_count = await repo.count_items(category_id=category_id)
>>>
>>> # Дорогих продуктов
>>> expensive_count = await repo.count_items(price__gte=5000)
```

---

### `exists_by_field()`

Проверка существования записи по полю.

**Сигнатура:**
```python
async def exists_by_field(
    field_name: str,
    field_value: Any
) -> bool
```

**Параметры:**
- `field_name` - название поля
- `field_value` - значение

**Возвращает:** `True` если exists

**Пример:**
```python
>>> # Проверить email
>>> email_exists = await repo.exists_by_field("email", "user@example.com")
>>>
>>> # Проверить код категории
>>> code_exists = await repo.exists_by_field("code", "tools")
>>>
>>> if code_exists:
...     raise ValueError("Код уже используется")
```

---

## Следующие разделы

- [**FILTERING.md**](./FILTERING.md) - Подробно о фильтрации
- [**ADVANCED.md**](./ADVANCED.md) - Продвинутые возможности
