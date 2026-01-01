# TODO

## Критично

### Синхронизировать данные чек-листа
**Файл**: `data/fixtures/checklist.json`  
**Проблема**: Сейчас в фикстуре только 1 категория с 11 задачами, должно быть 12 категорий с 98 задачами  
**Источник**: `../void-cms-frontend/shared/config/checklist-data.ts`

**Решение**:
1. Открыть файл фронтенда `shared/config/checklist-data.ts`
2. Скопировать весь массив `INITIAL_CHECKLIST_DATA`
3. Преобразовать TypeScript синтаксис в JSON:
   - Заменить одинарные кавычки на двойные
   - Убрать trailing commas
   - Удалить комментарии
4. Сохранить в `data/fixtures/checklist.json`

**Категории которые нужно добавить**:
- communication (8 задач)
- projects (10 задач)
- techstack (12 задач)
- git (9 задач)
- deploy (10 задач)
- legal (9 задач)
- sales (9 задач)
- testing (4 задачи)
- security (6 задач)
- support (5 задач)
- growth (5 задач)

