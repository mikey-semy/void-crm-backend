# Миграция на обновленные репозитории

## Обзор изменений

Все репозитории проекта были рефакторены для максимального использования `BaseRepository`. Это руководство поможет вам обновить существующий код.

## Критические изменения (Breaking Changes)

### 1. UserRepository

#### ❌ Удалены методы:
- `get_user_by_identifier_with_roles()`
- `get_user_with_roles()`

#### ✅ Замена:
```python
# Было:
user = await user_repo.get_user_by_identifier_with_roles("user@example.com")

# Стало:
user = await user_repo.get_user_by_identifier("user@example.com")
# Роли и компания загружаются автоматически через default_options!
```

```python
# Было:
user = await user_repo.get_user_with_roles(user_id)

# Стало:
user = await user_repo.get_item_by_id(user_id)
# Роли и компания загружаются автоматически!
```

### 2. ImageRepository

#### ❌ Удалены методы:
- `get_image_by_id()`
- `get_by_path()`
- `get_by_filename()`
- `exists_by_path()`
- `delete_image_by_id()`

#### ✅ Замена:
```python
# Было:
image = await image_repo.get_image_by_id(image_id)

# Стало:
image = await image_repo.get_item_by_id(image_id)
```

```python
# Было:
image = await image_repo.get_by_path("/uploads/photo.jpg")

# Стало:
image = await image_repo.get_item_by_field("path", "/uploads/photo.jpg")
```

```python
# Было:
exists = await image_repo.exists_by_path("/uploads/photo.jpg")

# Стало:
exists = await image_repo.exists_by_field("path", "/uploads/photo.jpg")
```

```python
# Было:
deleted = await image_repo.delete_image_by_id(image_id)

# Стало:
deleted = await image_repo.delete_item(image_id)
```

### 3. ProductRepository

#### ❌ Удалены переопределения:
- `get_item_by_id()` - теперь использует базовый метод с `default_options`
- `filter_by()` - теперь использует базовый метод с `default_options`

#### ✅ Изменения:
```python
# Было:
products = await product_repo.filter_by(is_active=True)
# Категории загружались через переопределенный метод

# Стало:
products = await product_repo.filter_by(is_active=True)
# Категории загружаются автоматически через default_options!
# Код не изменился, но работает быстрее
```

## Автоматическая миграция кода

### Поиск и замена в проекте

#### 1. UserRepository
```bash
# Найти все использования:
grep -r "get_user_by_identifier_with_roles" src/
grep -r "get_user_with_roles" src/

# Заменить:
# get_user_by_identifier_with_roles → get_user_by_identifier
# get_user_with_roles(user_id) → get_item_by_id(user_id)
```

#### 2. ImageRepository
```bash
# Найти все использования:
grep -r "get_image_by_id" src/
grep -r "get_by_path" src/
grep -r "get_by_filename" src/
grep -r "exists_by_path" src/
grep -r "delete_image_by_id" src/

# Заменить:
# get_image_by_id → get_item_by_id
# get_by_path(path) → get_item_by_field("path", path)
# get_by_filename(name) → get_item_by_field("filename", name)
# exists_by_path(path) → exists_by_field("path", path)
# delete_image_by_id → delete_item
```

## Примеры обновления сервисов

### До рефакторинга:

```python
class UserService:
    async def get_user_details(self, user_id: UUID):
        # Использовали специальный метод для загрузки ролей
        user = await self.user_repo.get_user_with_roles(user_id)
        if not user:
            raise UserNotFound()

        return UserDetailSchema(
            id=user.id,
            email=user.email,
            role=user.role,  # Роли загружены
            company_name=user.company.name  # Компания загружена
        )
```

### После рефакторинга:

```python
class UserService:
    async def get_user_details(self, user_id: UUID):
        # Используем базовый метод - роли загружаются автоматически!
        user = await self.user_repo.get_item_by_id(user_id)
        if not user:
            raise UserNotFound()

        return UserDetailSchema(
            id=user.id,
            email=user.email,
            role=user.role,  # Роли загружены автоматически
            company_name=user.company.name  # Компания загружена автоматически
        )
```

## Преимущества новой архитектуры

### 1. Меньше кода
```python
# Было: 219 строк в UserRepository
# Стало: 150 строк (-31%)
```

### 2. Автоматическая загрузка relationships
```python
# Было: нужно было явно вызывать методы с "_with_roles"
user = await repo.get_user_with_roles(user_id)

# Стало: relationships загружаются автоматически
user = await repo.get_item_by_id(user_id)
# user.role и user.company уже загружены!
```

### 3. Единообразие API
```python
# Все репозитории используют одинаковые методы:
product = await product_repo.get_item_by_id(product_id)
user = await user_repo.get_item_by_id(user_id)
company = await company_repo.get_item_by_id(company_id)
image = await image_repo.get_item_by_id(image_id)
```

### 4. Меньше импортов
```python
# Было:
from app.repository.v1.users import UserRepository
from app.repository.v1.products import ProductRepository

# Стало: можно использовать BaseRepository напрямую
from app.repository.v1.base import BaseRepository
from app.models.v1.users import UserModel

user_repo = BaseRepository(session, UserModel)
```

## Проверка совместимости

### Запуск тестов

```bash
# Все тесты репозиториев
pytest tests/unit/repository/ -v

# Функциональные тесты
pytest tests/functional/ -v

# Интеграционные тесты
pytest tests/integration/ -v
```

### Проверка использования удаленных методов

```bash
# Проверить, что удаленные методы нигде не используются
grep -r "get_user_by_identifier_with_roles" src/
grep -r "get_user_with_roles" src/
grep -r "get_image_by_id" src/
grep -r "get_by_path" src/
grep -r "exists_by_path" src/

# Если команды ничего не нашли - миграция завершена!
```

## FAQ

### Q: Почему удалили методы `get_user_with_roles`?
**A:** Теперь роли и компания загружаются автоматически через `default_options` для всех методов. Специальные методы больше не нужны.

### Q: Как загрузить дополнительные relationships?
**A:** Используйте метод `get_items_with_relations()`:

```python
users = await user_repo.get_items_with_relations(
    relation_options=[selectinload(UserModel.orders)],
    is_active=True
)
```

### Q: Что делать, если нужен метод без автозагрузки?
**A:** Переопределите метод в конкретном репозитории:

```python
class UserRepository(BaseRepository[UserModel]):
    default_options = [selectinload(UserModel.user_roles)]

    async def get_user_without_roles(self, user_id: UUID):
        # Используем execute_and_return_scalar без options
        stmt = select(UserModel).where(UserModel.id == user_id)
        return await self.execute_and_return_scalar(stmt)
```

### Q: Как мигрировать существующие сервисы?
**A:** Следуйте таблице замен выше. В большинстве случаев достаточно заменить имена методов.

## Поддержка

Если у вас возникли проблемы с миграцией:

1. Проверьте [REFACTORING_REPORT.md](./REFACTORING_REPORT.md) для деталей изменений
2. Изучите [README.md](./README.md) для документации по BaseRepository
3. Посмотрите примеры в обновленных репозиториях

## Чеклист миграции

- [ ] Найти все использования удаленных методов
- [ ] Заменить на базовые методы согласно таблице
- [ ] Запустить unit тесты репозиториев
- [ ] Запустить функциональные тесты
- [ ] Проверить логи на наличие N+1 запросов
- [ ] Обновить документацию сервисов
- [ ] Удалить неиспользуемые импорты

✅ После выполнения всех пунктов миграция завершена!
