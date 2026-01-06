"""
Роутер для OpenRouter Chat API.

API Reference:
- https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request
- https://openrouter.ai/docs/api/api-reference/completions/create-completions
"""

from fastapi import status

from app.core.dependencies.system_settings import AISettingsServiceDep
from app.core.security import CurrentAdminDep
from app.schemas.v1.openrouter import (
    ChatCompletionRequestSchema,
    ChatCompletionSimpleRequestSchema,
    ChatResponseSchema,
    OpenRouterChatResponseSchema,
    StructuredOutputRequestSchema,
    StructuredOutputResponseSchema,
)

from .base import BaseOpenRouterRouter


class AdminOpenRouterChatRouter(BaseOpenRouterRouter):
    """
    Роутер для Chat Completions OpenRouter.

    Используется для тестирования моделей из админки.

    Endpoints:
        POST /admin/openrouter/chat - Простой запрос
        POST /admin/openrouter/chat/messages - Полный чат с историей
        POST /admin/openrouter/chat/structured - Структурированный ответ
    """

    def __init__(self):
        """Инициализирует роутер."""
        super().__init__(prefix="admin/openrouter/chat", tags=["Admin - OpenRouter Chat"])

    def configure(self):
        """Настройка endpoint'ов."""

        @self.router.post(
            path="",
            response_model=ChatResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""\
## 💬 Простой Chat Completion

Отправляет простой промпт и получает ответ.

**OpenRouter API:** [POST /chat/completions](https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request)

### Request Body:
- **prompt** — Текст запроса
- **model** — ID модели (опционально)
- **temperature** — Температура 0.0-2.0 (опционально)
- **max_tokens** — Максимум токенов (опционально)
- **system_prompt** — Системный промпт (опционально)

### Returns:
- ID запроса
- Модель
- Ответ
- Токены (prompt/completion)
- Причина завершения
""",
        )
        async def simple_completion(
            data: ChatCompletionSimpleRequestSchema,
            service: AISettingsServiceDep,
            current_admin: CurrentAdminDep,
        ) -> ChatResponseSchema:
            """Простой chat completion."""
            try:
                client = await self._get_client(service)
                content = await client.complete(
                    prompt=data.prompt,
                    model=data.model,
                    temperature=data.temperature,
                    max_tokens=data.max_tokens,
                    system_prompt=data.system_prompt,
                )

                return ChatResponseSchema(
                    success=True,
                    message="Ответ получен",
                    data=OpenRouterChatResponseSchema(
                        id="",
                        model=data.model or client.default_model,
                        content=content,
                        tokens_prompt=0,
                        tokens_completion=0,
                    ),
                )
            except ValueError as e:
                return ChatResponseSchema(
                    success=False,
                    message=str(e),
                    data=OpenRouterChatResponseSchema(
                        id="",
                        model="",
                        content="",
                        tokens_prompt=0,
                        tokens_completion=0,
                    ),
                )

        @self.router.post(
            path="/messages",
            response_model=ChatResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""\
## 💬 Chat с историей сообщений

Отправляет полную историю чата и получает ответ.

**OpenRouter API:** [POST /chat/completions](https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request)

### Request Body:
- **messages** — История сообщений [{"role": "user|assistant|system", "content": "..."}]
- **model** — ID модели (опционально)
- **temperature** — Температура 0.0-2.0 (опционально)
- **max_tokens** — Максимум токенов (опционально)

### Returns:
- ID запроса
- Модель
- Ответ
- Токены
- Причина завершения
""",
        )
        async def chat_completion(
            data: ChatCompletionRequestSchema,
            service: AISettingsServiceDep,
            current_admin: CurrentAdminDep,
        ) -> ChatResponseSchema:
            """Chat completion с историей."""
            try:
                client = await self._get_client(service)
                response = await client.chat(
                    messages=[msg.model_dump() for msg in data.messages],
                    model=data.model,
                    temperature=data.temperature,
                    max_tokens=data.max_tokens,
                )

                return ChatResponseSchema(
                    success=True,
                    message="Ответ получен",
                    data=response,
                )
            except ValueError as e:
                return ChatResponseSchema(
                    success=False,
                    message=str(e),
                    data=OpenRouterChatResponseSchema(
                        id="",
                        model="",
                        content="",
                        tokens_prompt=0,
                        tokens_completion=0,
                    ),
                )

        @self.router.post(
            path="/structured",
            response_model=StructuredOutputResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""\
## 📋 Structured Output

Генерирует структурированный JSON ответ по схеме.

**OpenRouter API:** [POST /chat/completions](https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request) с `response_format`

### Request Body:
- **prompt** — Текст запроса
- **output_schema** — JSON Schema для ответа
- **model** — ID модели (опционально, рекомендуется с поддержкой JSON mode)
- **temperature** — Температура (опционально)
- **max_tokens** — Максимум токенов (опционально)

### Returns:
- Структурированный JSON согласно схеме
""",
        )
        async def structured_completion(
            data: StructuredOutputRequestSchema,
            service: AISettingsServiceDep,
            current_admin: CurrentAdminDep,
        ) -> StructuredOutputResponseSchema:
            """Structured output completion."""
            try:
                client = await self._get_client(service)
                result = await client.complete_structured(
                    prompt=data.prompt,
                    output_schema=data.output_schema,
                    model=data.model,
                    temperature=data.temperature,
                    max_tokens=data.max_tokens,
                )

                return StructuredOutputResponseSchema(
                    success=True,
                    message="Структурированный ответ получен",
                    data=result,
                )
            except ValueError as e:
                return StructuredOutputResponseSchema(
                    success=False,
                    message=str(e),
                    data={},
                )
