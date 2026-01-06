"""
Сервис для работы с системными настройками.

Модуль предоставляет:
- AISettingsService - управление AI настройками (эмбеддинги, LLM модели)
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.encryption import get_encryption_service
from app.core.settings import settings
from app.models.v1 import SystemSettingsKeys
from app.repository.v1.knowledge import KnowledgeArticleRepository
from app.repository.v1.system_settings import SystemSettingsRepository
from app.schemas.v1.system_settings import AISettingsSchema
from app.services.base import BaseService


class AISettingsService(BaseService):
    """
    Сервис для управления AI настройками.

    Обеспечивает:
    - Чтение/запись настроек эмбеддингов и LLM моделей
    - Безопасное хранение API ключа (шифрование)
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализирует сервис.

        Args:
            session: Асинхронная сессия SQLAlchemy
        """
        super().__init__(session)
        self.repository = SystemSettingsRepository(session)
        self.article_repository = KnowledgeArticleRepository(session)
        self.encryption = get_encryption_service()

    async def get_settings(self) -> AISettingsSchema:
        """
        Получает текущие AI настройки.

        Returns:
            AISettingsSchema с текущими настройками
        """
        ai_settings = settings.ai

        provider = await self.repository.get_value(
            SystemSettingsKeys.RAG_EMBEDDING_PROVIDER,
            ai_settings.RAG_DEFAULT_PROVIDER,
        )
        model = await self.repository.get_value(
            SystemSettingsKeys.RAG_EMBEDDING_MODEL,
            ai_settings.RAG_DEFAULT_MODEL,
        )
        dimension_str = await self.repository.get_value(
            SystemSettingsKeys.RAG_EMBEDDING_DIMENSION,
            str(ai_settings.RAG_DEFAULT_DIMENSION),
        )
        encrypted_key = await self.repository.get_value(
            SystemSettingsKeys.RAG_API_KEY,
            "",
        )

        # Получаем LLM модели
        llm_model = await self.repository.get_value(
            SystemSettingsKeys.AI_LLM_MODEL,
            "",
        )
        llm_fallback_model = await self.repository.get_value(
            SystemSettingsKeys.AI_LLM_FALLBACK_MODEL,
            "",
        )

        # Получаем количество статей с эмбеддингами
        indexed_count = await self.article_repository.count_with_embeddings()

        # Генерируем подсказку для API ключа
        api_key_hint = None
        if encrypted_key:
            api_key_hint = self._get_api_key_hint(encrypted_key)

        return AISettingsSchema(
            embedding_provider=provider,
            embedding_model=model,
            embedding_dimension=int(dimension_str) if dimension_str else ai_settings.RAG_DEFAULT_DIMENSION,
            has_api_key=bool(encrypted_key),
            api_key_hint=api_key_hint,
            indexed_articles_count=indexed_count,
            llm_model=llm_model if llm_model else None,
            llm_fallback_model=llm_fallback_model if llm_fallback_model else None,
        )

    async def update_settings(
        self,
        api_key: str | None = None,
        embedding_model: str | None = None,
        llm_model: str | None = None,
        llm_fallback_model: str | None = None,
    ) -> AISettingsSchema:
        """
        Обновляет AI настройки.

        Args:
            api_key: API ключ (будет зашифрован)
            embedding_model: Модель эмбеддингов
            llm_model: Основная LLM модель
            llm_fallback_model: Резервная LLM модель

        Returns:
            Обновлённые настройки
        """
        if api_key is not None:
            encrypted = self.encryption.encrypt(api_key)
            await self.repository.set_value(
                SystemSettingsKeys.RAG_API_KEY,
                encrypted,
                "Зашифрованный API ключ OpenRouter",
            )

        if embedding_model is not None:
            # Проверяем, изменилась ли модель
            current_model = await self.repository.get_value(
                SystemSettingsKeys.RAG_EMBEDDING_MODEL,
                "",
            )

            await self.repository.set_value(
                SystemSettingsKeys.RAG_EMBEDDING_MODEL,
                embedding_model,
                "Модель для эмбеддингов",
            )
            # Обновляем dimension на основе модели
            dimension = self._get_model_dimension(embedding_model)
            await self.repository.set_value(
                SystemSettingsKeys.RAG_EMBEDDING_DIMENSION,
                str(dimension),
                "Размерность вектора эмбеддинга",
            )

            # Если модель изменилась, сбрасываем все эмбеддинги
            if current_model and current_model != embedding_model:
                cleared_count = await self.article_repository.clear_all_embeddings()
                self.logger.warning(
                    "Модель эмбеддингов изменена с %s на %s. "
                    "Сброшено %d эмбеддингов. Требуется переиндексация.",
                    current_model,
                    embedding_model,
                    cleared_count,
                )

        if llm_model is not None:
            await self.repository.set_value(
                SystemSettingsKeys.AI_LLM_MODEL,
                llm_model,
                "Основная LLM модель",
            )

        if llm_fallback_model is not None:
            await self.repository.set_value(
                SystemSettingsKeys.AI_LLM_FALLBACK_MODEL,
                llm_fallback_model,
                "Резервная LLM модель",
            )

        self.logger.info("AI настройки обновлены")

        return await self.get_settings()

    async def get_decrypted_api_key(self) -> str | None:
        """
        Получает расшифрованный API ключ.

        Используется для выполнения запросов к провайдеру.

        Returns:
            Расшифрованный API ключ или None
        """
        encrypted = await self.repository.get_value(
            SystemSettingsKeys.RAG_API_KEY,
            "",
        )
        if not encrypted:
            return None

        return self.encryption.decrypt(encrypted)

    def _get_model_dimension(self, model: str) -> int:
        """
        Возвращает размерность вектора для модели.

        Использует settings.ai.get_embedding_dimension().

        Args:
            model: ID модели

        Returns:
            Размерность вектора
        """
        return settings.ai.get_embedding_dimension(model)

    def _get_api_key_hint(self, encrypted_key: str) -> str | None:
        """
        Генерирует подсказку для API ключа (первые и последние символы).

        Args:
            encrypted_key: Зашифрованный API ключ

        Returns:
            Подсказка вида "sk-or...7x2f" или None
        """
        try:
            decrypted = self.encryption.decrypt(encrypted_key)
            if not decrypted or len(decrypted) < 8:
                return None
            # Показываем первые 5 и последние 4 символа
            return f"{decrypted[:5]}...{decrypted[-4:]}"
        except Exception:
            return None
