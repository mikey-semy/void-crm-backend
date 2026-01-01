"""
Скрипт для синхронизации данных чек-листа с фронтенда.
Читает TypeScript файл и генерирует JSON фикстуру.
"""
import json
import re
from pathlib import Path

# Путь к фронтенду
FRONTEND_PATH = Path(__file__).parent.parent.parent / "void-cms-frontend"
FRONTEND_DATA = FRONTEND_PATH / "shared" / "config" / "checklist-data.ts"

# Путь к фикстурам бэкенда
BACKEND_FIXTURES = Path(__file__).parent.parent / "data" / "fixtures" / "checklist.json"


def parse_typescript_data(ts_content: str) -> list:
    """Парсит TypeScript файл и извлекает данные категорий."""
    # Находим массив INITIAL_CHECKLIST_DATA
    match = re.search(r'export const INITIAL_CHECKLIST_DATA.*?=\s*\[(.*)\]', ts_content, re.DOTALL)
    if not match:
        raise ValueError("Не удалось найти INITIAL_CHECKLIST_DATA")
    
    # Упрощенный парсер для данных
    # В реальности лучше использовать специализированный парсер
    # Но для наших структурированных данных подойдет JSON парсинг после замены TypeScript на JSON
    
    data_str = match.group(1)
    
    # Заменяем TypeScript синтаксис на JSON
    # Заменяем одинарные кавычки на двойные
    data_str = data_str.replace("'", '"')
    
    # Убираем trailing commas перед закрывающими скобками
    data_str = re.sub(r',\s*([\]}])', r'\1', data_str)
    
    # Оборачиваем в массив
    json_str = f'[{data_str}]'
    
    try:
        data = json.loads(json_str)
        return data
    except json.JSONDecodeError as e:
        print(f"Ошибка парсинга JSON: {e}")
        # Сохраним для отладки
        with open("debug_output.json", "w", encoding="utf-8") as f:
            f.write(json_str)
        raise


def main():
    """Основная функция."""
    print("🔄 Синхронизация данных чек-листа с фронтенда...")
    
    if not FRONTEND_DATA.exists():
        print(f"❌ Файл фронтенда не найден: {FRONTEND_DATA}")
        return 1
    
    # Читаем TypeScript файл
    ts_content = FRONTEND_DATA.read_text(encoding="utf-8")
    
    # Парсим данные
    try:
        categories = parse_typescript_data(ts_content)
        print(f"✅ Найдено категорий: {len(categories)}")
        
        # Подсчет задач
        total_tasks = sum(len(cat.get('tasks', [])) for cat in categories)
        print(f"✅ Найдено задач: {total_tasks}")
        
    except Exception as e:
        print(f"❌ Ошибка парсинга: {e}")
        return 1
    
    # Создаем директорию, если её нет
    BACKEND_FIXTURES.parent.mkdir(parents=True, exist_ok=True)
    
    # Сохраняем JSON
    with open(BACKEND_FIXTURES, "w", encoding="utf-8") as f:
        json.dump(categories, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Данные сохранены в {BACKEND_FIXTURES}")
    print(f"📊 Категорий: {len(categories)}, Задач: {total_tasks}")
    
    return 0


if __name__ == "__main__":
    exit(main())
