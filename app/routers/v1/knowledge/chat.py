"""
Роутер для RAG-чата по базе знаний.

Позволяет общаться с AI-ассистентом, который использует контекст из статей базы знаний.
"""

import logging

from app.core.dependencies.knowledge import KnowledgeServiceDep
from app.routers.base import BaseRouter
from app.schemas.v1.knowledge import (
    KnowledgeChatDataSchema,
    KnowledgeChatRequestSchema,
    KnowledgeChatResponseSchema,
    KnowledgeChatSourceSchema,
)

logger = logging.getLogger(__name__)


class KnowledgeChatRouter(BaseRouter):
    """
    Роутер для RAG-чата по базе знаний.

    Public endpoints:
        POST /knowledge/chat - Отправить сообщение и получить ответ с контекстом из базы знаний
    """

    def __init__(self):
        """Инициализирует KnowledgeChatRouter."""
        super().__init__(prefix="knowledge/chat", tags=["Knowledge Base - Chat"])

    def configure(self):
        """Настройка endpoint'ов для чата."""

        @self.router.post(
            path="",
            response_model=KnowledgeChatResponseSchema,
            description="""\
## 💬 RAG-чат по базе знаний

Отправляет сообщение AI-ассистенту, который отвечает с использованием контекста из статей базы знаний.

### Как это работает:
1. LLM анализирует историю диалога и формирует поисковый запрос
2. Семантический поиск находит релевантные фрагменты статей
3. LLM генерирует ответ на основе контекста и истории диалога
4. В ответе возвращаются источники (статьи), которые были использованы

### Request Body:
- **messages** — История сообщений [{role: "user"|"assistant", content: "..."}]
- **use_context** — Использовать контекст из базы знаний (по умолчанию true)

### Returns:
- **content** — Ответ ассистента
- **sources** — Список источников (статей) из базы знаний
- **model** — Использованная LLM модель

### Example:
```json
{
  "messages": [
    {"role": "user", "content": "Как настроить Docker?"}
  ]
}
```
""",
        )
        async def chat(
            data: KnowledgeChatRequestSchema,
            knowledge_service: KnowledgeServiceDep,
        ) -> KnowledgeChatResponseSchema:
            """RAG-чат с контекстом из базы знаний."""
            # Вызываем метод сервиса
            result = await knowledge_service.chat(
                messages=data.messages,
                use_context=data.use_context,
            )

            # Преобразуем sources в схемы
            sources = [
                KnowledgeChatSourceSchema(
                    id=src["id"],
                    title=src["title"],
                    slug=src["slug"],
                )
                for src in result["sources"]
            ]

            return KnowledgeChatResponseSchema(
                success=True,
                message="Ответ получен",
                data=KnowledgeChatDataSchema(
                    content=result["content"],
                    sources=sources,
                    model=result["model"],
                    needs_clarification=result.get("needs_clarification", False),
                    clarification_options=result.get("clarification_options", []),
                    additional_context_loaded=result.get(
                        "additional_context_loaded", False
                    ),
                ),
            )
