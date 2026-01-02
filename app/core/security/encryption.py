"""
Утилиты для шифрования/дешифрования данных.

Используется для безопасного хранения паролей и других чувствительных данных.
"""

import base64
import logging

from cryptography.fernet import Fernet

from app.core.settings import Settings

logger = logging.getLogger(__name__)


class EncryptionService:
    """
    Сервис для шифрования/дешифрования данных.

    Использует Fernet (симметричное шифрование) из cryptography.
    """

    def __init__(self, settings: Settings | None = None):
        """
        Инициализация сервиса шифрования.

        Args:
            settings: Настройки приложения (для получения ключа)
        """
        self.settings = settings or Settings()
        self._cipher = None

    def _get_cipher(self) -> Fernet:
        """
        Получить объект Fernet cipher.

        Использует TOKEN_SECRET_KEY из настроек для генерации ключа шифрования.

        Returns:
            Fernet cipher
        """
        if self._cipher is None:
            # Используем TOKEN_SECRET_KEY из настроек
            # Fernet требует 32-байтовый URL-safe base64-encoded ключ
            secret = self.settings.TOKEN_SECRET_KEY.get_secret_value()
            key = base64.urlsafe_b64encode(secret.encode()[:32].ljust(32, b"\0"))
            self._cipher = Fernet(key)
        return self._cipher

    def encrypt(self, plaintext: str) -> str:
        """
        Зашифровать строку.

        Args:
            plaintext: Открытый текст для шифрования

        Returns:
            Зашифрованная строка (base64)
        """
        if not plaintext:
            return ""

        try:
            cipher = self._get_cipher()
            encrypted_bytes = cipher.encrypt(plaintext.encode())
            return encrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            raise

    def decrypt(self, encrypted: str) -> str:
        """
        Дешифровать строку.

        Args:
            encrypted: Зашифрованная строка (base64)

        Returns:
            Расшифрованный текст
        """
        if not encrypted:
            return ""

        try:
            cipher = self._get_cipher()
            decrypted_bytes = cipher.decrypt(encrypted.encode())
            return decrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            raise


# Singleton instance
_encryption_service: EncryptionService | None = None


def get_encryption_service() -> EncryptionService:
    """
    Получить singleton instance EncryptionService.

    Returns:
        EncryptionService instance
    """
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service
