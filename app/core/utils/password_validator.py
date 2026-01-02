"""
Утилиты для валидации паролей.

Модуль содержит функции для проверки паролей на соответствие требованиям безопасности.
Переиспользуется в регистрации, смене пароля и сбросе пароля.
"""


def validate_password_strength(password: str) -> None:
    """
    Валидирует пароль на соответствие требованиям безопасности.

    Проверяет:
    - Минимальную длину (8 символов)
    - Наличие заглавных и строчных букв
    - Наличие цифр
    - Наличие специальных символов

    Args:
        password: Пароль для валидации.

    Raises:
        ValueError: Если пароль не соответствует требованиям безопасности.

    Example:
        >>> validate_password_strength("SecurePass123!")  # OK
        >>> validate_password_strength("weak")  # ValueError

    Note:
        Эта функция переиспользуется в:
        - RegistrationRequestSchema (регистрация)
        - AuthService.change_password (смена пароля)
        - AuthService.confirm_password_reset (сброс пароля)
    """
    # Проверка длины
    if len(password) < 8:
        raise ValueError("Пароль должен содержать минимум 8 символов")

    # Проверка наличия заглавной буквы
    if not any(c.isupper() for c in password):
        raise ValueError("Пароль должен содержать хотя бы одну заглавную букву")

    # Проверка наличия строчной буквы
    if not any(c.islower() for c in password):
        raise ValueError("Пароль должен содержать хотя бы одну строчную букву")

    # Проверка наличия цифры
    if not any(c.isdigit() for c in password):
        raise ValueError("Пароль должен содержать хотя бы одну цифру")

    # Проверка наличия специального символа
    special_chars = "!@#$%^&*()-_=+[]{}|;:',.<>?/`~"
    if not any(c in special_chars for c in password):
        raise ValueError(
            f"Пароль должен содержать хотя бы один специальный символ: {special_chars}"
        )
