# Void CRM MCP Server

MCP сервер для интеграции Void CRM с Claude Code.

## Модули

### Knowledge Base (База знаний)
- **Семантический поиск (RAG)** — поиск статей по смыслу через OpenRouter embeddings
- **Полнотекстовый поиск** — быстрый поиск по ключевым словам
- **Чтение статей** — получение полного Markdown контента
- **Сниппеты кода** — извлечение примеров кода по тегам
- **CRUD операции** — создание, редактирование, удаление статей

### Планируемые модули
- **Tasks** — Задания клиентов (ТЗ, требования)
- **Checklist** — Чек-листы проектов
- **Clients** — Информация о клиентах

## Установка

```bash
cd mcp-servers/void-crm
npm install
npm run build
```

## Настройка Claude Code

Добавьте в `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "void-crm": {
      "command": "node",
      "args": ["dist/index.js"],
      "cwd": "c:/Users/Mike/Projects/void-crm-backend/mcp-servers/void-crm",
      "env": {
        "VOID_API_URL": "http://localhost:8000/api/v1",
        "VOID_API_KEY": "sk-or-v1-..."
      }
    }
  }
}
```

### Переменные окружения

| Переменная | Описание | Пример |
|------------|----------|--------|
| `VOID_API_URL` | URL API Void CRM | `http://localhost:8000/api/v1` |
| `VOID_API_KEY` | API ключ OpenRouter | `sk-or-v1-...` |
| `VOID_TIMEOUT` | Таймаут запросов (мс) | `30000` |

## Доступные tools

### Knowledge Base

| Tool | Описание |
|------|----------|
| `search_knowledge` | Семантический/полнотекстовый поиск |
| `read_article` | Чтение статьи по slug |
| `list_categories` | Список категорий |
| `list_tags` | Популярные теги |
| `get_snippets` | Сниппеты кода по тегу |
| `create_article` | Создание статьи |
| `update_article` | Обновление статьи |
| `delete_article` | Удаление статьи |
| `find_similar` | Похожие статьи |
| `index_articles` | Индексация для RAG |

## Структура проекта

```
src/
├── index.ts          # Entry point
├── config.ts         # Конфигурация
├── server.ts         # MCP Server
├── api/
│   └── client.ts     # HTTP клиент
└── tools/
    ├── index.ts      # Экспорт всех tools
    └── knowledge.ts  # Knowledge Base tools
```

## Добавление нового модуля

1. Создать файл `src/tools/[module].ts`:
```typescript
import type { Tool } from "@modelcontextprotocol/sdk/types.js";

export const MODULE_TOOLS: Tool[] = [...];

export async function handleModuleTool(
  name: string,
  args: Record<string, unknown>,
  client: VoidApiClient
): Promise<unknown> { ... }

export function isModuleTool(name: string): boolean { ... }
```

2. Экспортировать в `src/tools/index.ts`

3. Подключить в `src/server.ts`:
```typescript
import { MODULE_TOOLS, handleModuleTool, isModuleTool } from "./tools/module.js";

function getAllTools(): Tool[] {
  return [...KNOWLEDGE_TOOLS, ...MODULE_TOOLS];
}

// В handleToolCall:
if (isModuleTool(name)) {
  return await handleModuleTool(name, args, this.client);
}
```

## Разработка

```bash
npm run dev        # Режим разработки
npm run typecheck  # Проверка типов
npm run build      # Сборка
```

## Требования

- Node.js >= 18
- Void CRM Backend с pgvector
- OpenRouter API ключ

## Лицензия

MIT
