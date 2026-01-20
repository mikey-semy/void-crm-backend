"""
Сервис для работы с системными настройками.

Модуль предоставляет:
- AISettingsService - управление AI настройками (эмбеддинги, LLM модели)
- Управление промптами
- Глобальные настройки поиска
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.encryption import get_encryption_service
from app.core.settings import settings
from app.models.v1 import SystemSettingsKeys
from app.repository.v1.knowledge import KnowledgeArticleRepository
from app.repository.v1.system_settings import SystemSettingsRepository
from app.schemas.v1.system_settings import (
    AISettingsSchema,
    PromptListSchema,
    PromptSchema,
    PromptType,
    SearchMode,
    SearchSettingsSchema,
)
from app.services.base import BaseService


# Дефолтные промпты
DEFAULT_PROMPTS: dict[PromptType, dict] = {
    PromptType.KNOWLEDGE_CHAT: {
        "name": "Чат по базе знаний",
        "description": "Системный промпт для RAG-чата. Используется при ответах на вопросы пользователей.",
        "content": """Ты — AI-ассистент базы знаний. Твоя задача — помогать пользователям находить информацию и отвечать на вопросы.

Правила:
1. Отвечай на русском языке
2. Используй информацию из предоставленного контекста для ответов
3. Если в контексте есть только частичная информация — дай ответ на основе того что есть
4. Если в контексте нет релевантной информации — честно скажи об этом
5. Давай развёрнутые, полные ответы. Не обрывай мысль на середине
6. Если пользователь приветствует тебя, поприветствуй в ответ и предложи помощь
7. ВАЖНО: Всегда завершай свои ответы полностью""",
    },
    PromptType.DESCRIPTION_GENERATOR: {
        "name": "Генератор описаний",
        "description": "Промпт для автогенерации описания статьи на основе заголовка и контента.",
        "content": """Напиши краткое описание для статьи базы знаний.
Описание должно быть на русском языке, 1-2 предложения, без кавычек.
Описание должно кратко передавать суть статьи и привлекать читателя.""",
    },
    PromptType.SEARCH_QUERY_EXTRACTOR: {
        "name": "Извлечение поискового запроса",
        "description": "Промпт для извлечения оптимального поискового запроса из диалога с пользователем.",
        "content": """Проанализируй диалог и определи, нужен ли поиск по базе знаний.

Правила:
1. Если это приветствие или общая фраза (привет, спасибо, пока) - верни NONE
2. Если пользователь задаёт уточняющий вопрос (дальше, ещё, продолжи, подробнее) - сформируй запрос на основе предыдущего контекста диалога
3. Если пользователь задаёт новый вопрос - извлеки ключевые слова для поиска

ВАЖНО: Верни ТОЛЬКО поисковый запрос (3-10 слов) или слово NONE. Без объяснений.""",
    },
}


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

        Оптимизировано: загружает все настройки одним SQL запросом.

        Returns:
            AISettingsSchema с текущими настройками
        """
        ai_settings = settings.ai

        # Загружаем все настройки одним запросом (вместо 7 отдельных)
        keys = [
            SystemSettingsKeys.AI_ENABLED,
            SystemSettingsKeys.RAG_EMBEDDING_PROVIDER,
            SystemSettingsKeys.RAG_EMBEDDING_MODEL,
            SystemSettingsKeys.RAG_EMBEDDING_DIMENSION,
            SystemSettingsKeys.RAG_API_KEY,
            SystemSettingsKeys.AI_LLM_MODEL,
            SystemSettingsKeys.AI_LLM_FALLBACK_MODEL,
        ]
        defaults = {
            SystemSettingsKeys.AI_ENABLED: "true",
            SystemSettingsKeys.RAG_EMBEDDING_PROVIDER: ai_settings.RAG_DEFAULT_PROVIDER,
            SystemSettingsKeys.RAG_EMBEDDING_MODEL: ai_settings.RAG_DEFAULT_MODEL,
            SystemSettingsKeys.RAG_EMBEDDING_DIMENSION: str(ai_settings.RAG_DEFAULT_DIMENSION),
            SystemSettingsKeys.RAG_API_KEY: "",
            SystemSettingsKeys.AI_LLM_MODEL: "",
            SystemSettingsKeys.AI_LLM_FALLBACK_MODEL: "",
        }
        values = await self.repository.get_values_bulk(keys, defaults)

        # Распаковываем значения
        ai_enabled = values[SystemSettingsKeys.AI_ENABLED].lower() == "true"
        provider = values[SystemSettingsKeys.RAG_EMBEDDING_PROVIDER]
        model = values[SystemSettingsKeys.RAG_EMBEDDING_MODEL]
        dimension_str = values[SystemSettingsKeys.RAG_EMBEDDING_DIMENSION]
        encrypted_key = values[SystemSettingsKeys.RAG_API_KEY]
        llm_model = values[SystemSettingsKeys.AI_LLM_MODEL]
        llm_fallback_model = values[SystemSettingsKeys.AI_LLM_FALLBACK_MODEL]

        # Получаем количество статей с эмбеддингами
        indexed_count = await self.article_repository.count_with_embeddings()

        # Генерируем подсказку для API ключа
        api_key_hint = None
        if encrypted_key:
            api_key_hint = self._get_api_key_hint(encrypted_key)

        return AISettingsSchema(
            ai_enabled=ai_enabled,
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
        ai_enabled: bool | None = None,
        api_key: str | None = None,
        embedding_model: str | None = None,
        llm_model: str | None = None,
        llm_fallback_model: str | None = None,
    ) -> AISettingsSchema:
        """
        Обновляет AI настройки.

        Args:
            ai_enabled: Включить/выключить AI функции
            api_key: API ключ (будет зашифрован)
            embedding_model: Модель эмбеддингов
            llm_model: Основная LLM модель
            llm_fallback_model: Резервная LLM модель

        Returns:
            Обновлённые настройки
        """
        if ai_enabled is not None:
            await self.repository.set_value(
                SystemSettingsKeys.AI_ENABLED,
                "true" if ai_enabled else "false",
                "AI функции включены/выключены",
            )

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

    # ==================== ПРОМПТЫ ====================

    def _get_prompt_key(self, prompt_type: PromptType) -> str:
        """Возвращает ключ настройки для типа промпта."""
        mapping = {
            PromptType.KNOWLEDGE_CHAT: SystemSettingsKeys.AI_PROMPT_KNOWLEDGE_CHAT,
            PromptType.DESCRIPTION_GENERATOR: SystemSettingsKeys.AI_PROMPT_DESCRIPTION_GENERATOR,
            PromptType.SEARCH_QUERY_EXTRACTOR: SystemSettingsKeys.AI_PROMPT_SEARCH_QUERY_EXTRACTOR,
        }
        return mapping[prompt_type]

    async def get_prompts(self) -> PromptListSchema:
        """
        Получает список всех промптов.

        Returns:
            PromptListSchema со всеми промптами
        """
        prompts: list[PromptSchema] = []

        for prompt_type, defaults in DEFAULT_PROMPTS.items():
            key = self._get_prompt_key(prompt_type)
            custom_content = await self.repository.get_value(key, "")

            is_default = not bool(custom_content)
            content = custom_content if custom_content else defaults["content"]

            prompts.append(
                PromptSchema(
                    type=prompt_type,
                    name=defaults["name"],
                    description=defaults["description"],
                    content=content,
                    is_default=is_default,
                )
            )

        return PromptListSchema(prompts=prompts)

    async def get_prompt(self, prompt_type: PromptType) -> PromptSchema:
        """
        Получает один промпт по типу.

        Args:
            prompt_type: Тип промпта

        Returns:
            PromptSchema с промптом
        """
        defaults = DEFAULT_PROMPTS[prompt_type]
        key = self._get_prompt_key(prompt_type)
        custom_content = await self.repository.get_value(key, "")

        is_default = not bool(custom_content)
        content = custom_content if custom_content else defaults["content"]

        return PromptSchema(
            type=prompt_type,
            name=defaults["name"],
            description=defaults["description"],
            content=content,
            is_default=is_default,
        )

    async def update_prompt(self, prompt_type: PromptType, content: str) -> PromptSchema:
        """
        Обновляет текст промпта.

        Args:
            prompt_type: Тип промпта
            content: Новый текст промпта

        Returns:
            Обновлённый PromptSchema
        """
        key = self._get_prompt_key(prompt_type)
        defaults = DEFAULT_PROMPTS[prompt_type]

        await self.repository.set_value(
            key,
            content,
            f"Кастомный промпт: {defaults['name']}",
        )

        self.logger.info("Промпт '%s' обновлён", defaults["name"])

        return await self.get_prompt(prompt_type)

    async def reset_prompt(self, prompt_type: PromptType) -> PromptSchema:
        """
        Сбрасывает промпт к дефолтному значению.

        Args:
            prompt_type: Тип промпта

        Returns:
            PromptSchema с дефолтным промптом
        """
        key = self._get_prompt_key(prompt_type)
        defaults = DEFAULT_PROMPTS[prompt_type]

        await self.repository.delete_by_key(key)

        self.logger.info("Промпт '%s' сброшен к дефолтному", defaults["name"])

        return await self.get_prompt(prompt_type)

    async def get_prompt_content(self, prompt_type: PromptType) -> str:
        """
        Получает текст промпта для использования в коде.

        Args:
            prompt_type: Тип промпта

        Returns:
            Текст промпта (кастомный или дефолтный)
        """
        key = self._get_prompt_key(prompt_type)
        custom_content = await self.repository.get_value(key, "")

        if custom_content:
            return custom_content

        return DEFAULT_PROMPTS[prompt_type]["content"]

    # ==================== НАСТРОЙКИ ПОИСКА ====================

    async def get_search_settings(self) -> SearchSettingsSchema:
        """
        Получает глобальные настройки поиска.

        Returns:
            SearchSettingsSchema с настройками
        """
        keys = [
            SystemSettingsKeys.SEARCH_DEFAULT_MODE,
            SystemSettingsKeys.SEARCH_SIMILARITY_THRESHOLD,
            SystemSettingsKeys.SEARCH_FTS_WEIGHT,
            SystemSettingsKeys.SEARCH_SEMANTIC_WEIGHT,
        ]
        defaults = {
            SystemSettingsKeys.SEARCH_DEFAULT_MODE: SearchMode.HYBRID.value,
            SystemSettingsKeys.SEARCH_SIMILARITY_THRESHOLD: "0.5",
            SystemSettingsKeys.SEARCH_FTS_WEIGHT: "1.0",
            SystemSettingsKeys.SEARCH_SEMANTIC_WEIGHT: "1.0",
        }
        values = await self.repository.get_values_bulk(keys, defaults)

        return SearchSettingsSchema(
            default_mode=SearchMode(values[SystemSettingsKeys.SEARCH_DEFAULT_MODE]),
            similarity_threshold=float(values[SystemSettingsKeys.SEARCH_SIMILARITY_THRESHOLD]),
            fts_weight=float(values[SystemSettingsKeys.SEARCH_FTS_WEIGHT]),
            semantic_weight=float(values[SystemSettingsKeys.SEARCH_SEMANTIC_WEIGHT]),
        )

    async def update_search_settings(
        self,
        default_mode: SearchMode | None = None,
        similarity_threshold: float | None = None,
        fts_weight: float | None = None,
        semantic_weight: float | None = None,
    ) -> SearchSettingsSchema:
        """
        Обновляет настройки поиска.

        Args:
            default_mode: Режим поиска по умолчанию
            similarity_threshold: Порог схожести
            fts_weight: Вес FTS
            semantic_weight: Вес семантики

        Returns:
            Обновлённые настройки
        """
        if default_mode is not None:
            await self.repository.set_value(
                SystemSettingsKeys.SEARCH_DEFAULT_MODE,
                default_mode.value,
                "Режим поиска по умолчанию",
            )

        if similarity_threshold is not None:
            await self.repository.set_value(
                SystemSettingsKeys.SEARCH_SIMILARITY_THRESHOLD,
                str(similarity_threshold),
                "Порог схожести для семантического поиска",
            )

        if fts_weight is not None:
            await self.repository.set_value(
                SystemSettingsKeys.SEARCH_FTS_WEIGHT,
                str(fts_weight),
                "Вес FTS в гибридном поиске",
            )

        if semantic_weight is not None:
            await self.repository.set_value(
                SystemSettingsKeys.SEARCH_SEMANTIC_WEIGHT,
                str(semantic_weight),
                "Вес семантического поиска",
            )

        self.logger.info("Настройки поиска обновлены")

        return await self.get_search_settings()
