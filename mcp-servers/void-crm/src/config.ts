/**
 * Конфигурация MCP сервера.
 */

export interface Config {
  /** URL базового API */
  apiUrl: string;
  /** API ключ пользователя (OpenRouter) */
  apiKey: string;
  /** Таймаут HTTP запросов в мс */
  timeout: number;
}

/**
 * Загружает конфигурацию из переменных окружения.
 */
export function loadConfig(): Config {
  const apiUrl = process.env.VOID_API_URL;
  const apiKey = process.env.VOID_API_KEY;

  if (!apiUrl) {
    throw new Error("VOID_API_URL environment variable is required");
  }

  if (!apiKey) {
    throw new Error("VOID_API_KEY environment variable is required");
  }

  return {
    apiUrl: apiUrl.replace(/\/$/, ""), // Remove trailing slash
    apiKey,
    timeout: parseInt(process.env.VOID_TIMEOUT || "30000", 10),
  };
}
