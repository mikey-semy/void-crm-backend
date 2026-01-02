"""
Модуль для работы с паролями.

Предоставляет класс PasswordManager для:
- Хеширования паролей через Argon2
- Проверки паролей
- Валидации силы пароля
- Генерации случайных паролей
"""

import logging
import re
import secrets
import string

import passlib
from passlib.context import CryptContext

from app.core.exceptions import WeakPasswordError
from app.core.settings import settings

pwd_context = CryptContext(**settings.crypt_context_params)

logger = logging.getLogger(__name__)


class PasswordManager:
    """
    Класс для хеширования и проверки паролей.

    Предоставляет методы для хеширования паролей и проверки хешей.
    """

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Генерирует хеш пароля с использованием bcrypt.

        Args:
            password: Пароль для хеширования

        Returns:
            Хешированный пароль
        """
        return pwd_context.hash(password)

    @staticmethod
    def verify(hashed_password: str, plain_password: str) -> bool:
        """
        Проверяет, соответствует ли переданный пароль хешу.

        Args:
            hashed_password: Хеш пароля.
            plain_password: Пароль для проверки.

        Returns:
            True, если пароль соответствует хешу, иначе False.
        """
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except passlib.exc.UnknownHashError:
            logger.warning("Неизвестный формат хеша пароля")
            return False

    @staticmethod
    def validate_password_strength(password: str, username: str = None) -> str:
        """
        Проверяет сложность пароля на соответствие требованиям безопасности.

        Args:
            password: Пароль для проверки
            username: Имя пользователя для проверки, что пароль его не содержит

        Returns:
            Проверенный пароль, если он соответствует требованиям

        Raises:
            WeakPasswordError: Если пароль не соответствует требованиям безопасности
        """
        errors = []

        # Проверка минимальной длины
        if len(password) < settings.PASSWORD_MIN_LENGTH:
            errors.append("Пароль должен содержать минимум 8 символов")

        # Проверка на наличие заглавной буквы
        if settings.PASSWORD_REQUIRE_UPPER and not re.search(r"[A-ZА-Я]", password):
            errors.append("Пароль должен содержать хотя бы одну заглавную букву")

        # Проверка на наличие строчной буквы
        if settings.PASSWORD_REQUIRE_LOWER and not re.search(r"[a-zа-я]", password):
            errors.append("Пароль должен содержать хотя бы одну строчную букву")

        # Проверка на наличие цифры
        if settings.PASSWORD_REQUIRE_DIGIT and not re.search(r"\d", password):
            errors.append("Пароль должен содержать хотя бы одну цифру")

        # Проверка на наличие специального символа
        if settings.PASSWORD_REQUIRE_SPECIAL and not re.search(
            r'[!@#$%^&*(),.?":{}|<>]', password
        ):
            errors.append("Пароль должен содержать хотя бы один специальный символ")

        # Проверка распространенных последовательностей
        if any(seq in password.lower() for seq in settings.PASSWORD_COMMON_SEQUENCES):
            errors.append(
                "Пароль не должен содержать распространенные последовательности"
            )

        # Проверка, что пароль не содержит имя пользователя
        if settings.PASSWORD_FORBID_USERNAME and username and len(username) > 3:
            if username.lower() in password.lower():
                errors.append("Пароль не должен содержать имя пользователя")

        if errors:
            # Вызываем существующее исключение с детальным сообщением об ошибках
            raise WeakPasswordError("; ".join(errors))

        return password

    @staticmethod
    def generate_password(length: int = None) -> str:
        """
        Генерирует случайный пароль, соответствующий политике безопасности.

        Args:
            length: Длина пароля (по умолчанию из настроек)

        Returns:
            str: Случайный пароль
        """
        length = length or settings.PASSWORD_MIN_LENGTH
        if length < settings.PASSWORD_MIN_LENGTH:
            length = settings.PASSWORD_MIN_LENGTH

        lowercase = string.ascii_lowercase if settings.PASSWORD_REQUIRE_LOWER else ""
        uppercase = string.ascii_uppercase if settings.PASSWORD_REQUIRE_UPPER else ""
        digits = string.digits if settings.PASSWORD_REQUIRE_DIGIT else ""
        special = (
            "!@#$%^&*()_+-=[]{}|;:,.<>?" if settings.PASSWORD_REQUIRE_SPECIAL else ""
        )

        categories = []
        if lowercase:
            categories.append(secrets.choice(lowercase))
        if uppercase:
            categories.append(secrets.choice(uppercase))
        if digits:
            categories.append(secrets.choice(digits))
        if special:
            categories.append(secrets.choice(special))

        all_chars = lowercase + uppercase + digits + special
        remaining_length = length - len(categories)
        categories.extend(secrets.choice(all_chars) for _ in range(remaining_length))

        secrets.SystemRandom().shuffle(categories)
        return "".join(categories)
