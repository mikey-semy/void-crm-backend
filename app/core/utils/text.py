"""
Утилиты для работы с текстом.

Модуль предоставляет функции для обработки текста:
- Генерация slug с транслитерацией русских букв (ГОСТ 7.79-2000)
- Очистка и нормализация строк
"""

import re

# Словарь транслитерации русских букв в латиницу (ГОСТ 7.79-2000)
TRANSLIT_MAP = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "i",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "h",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "sch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "iu",
    "я": "ia",
}


def transliterate(text: str) -> str:
    """
    Транслитерирует русский текст в латиницу.

    Использует ГОСТ 7.79-2000 систему транслитерации.
    Оставляет английские буквы без изменений.

    Args:
        text: Текст для транслитерации

    Returns:
        str: Транслитерированный текст

    Example:
        >>> transliterate("Привет мир")
        "privet mir"
        >>> transliterate("Hello Мир")
        "hello mir"
        >>> transliterate("Настройка ESLint")
        "nastroika eslint"
    """
    if not text:
        return ""

    text = text.lower()
    result = []
    for char in text:
        result.append(TRANSLIT_MAP.get(char, char))

    return "".join(result)


def generate_slug(name: str, transliterate_cyrillic: bool = True) -> str:
    """
    Генерирует URL-friendly slug из названия.

    Обрабатывает текст для использования в URL:
    - Опционально транслитерирует кириллицу (по ГОСТ 7.79-2000)
    - Приводит к нижнему регистру
    - Удаляет спецсимволы
    - Заменяет пробелы на дефисы
    - Ограничивает длину до 255 символов

    Args:
        name: Название для преобразования
        transliterate_cyrillic: Транслитерировать ли русские буквы (по умолчанию True)

    Returns:
        str: Сгенерированный slug

    Example:
        >>> generate_slug("Настройка Docker")
        "nastroika-docker"
        >>> generate_slug("Best Practices для Python")
        "best-practices-dlia-python"
        >>> generate_slug("React + TypeScript (2024)")
        "react-typescript-2024"
    """
    if not name:
        return ""

    slug = name.strip()

    # Транслитерация кириллицы если нужно
    if transliterate_cyrillic:
        slug = transliterate(slug)
    else:
        slug = slug.lower()

    # Удаляем всё кроме букв, цифр, пробелов и дефисов
    slug = re.sub(r"[^\w\s-]", "", slug)

    # Заменяем последовательности пробелов/подчеркиваний/дефисов на один дефис
    slug = re.sub(r"[-\s_]+", "-", slug)

    # Убираем дефисы в начале и конце
    slug = slug.strip("-")

    # Ограничиваем длину
    return slug[:255]
