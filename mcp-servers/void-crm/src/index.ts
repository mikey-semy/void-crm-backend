/**
 * Entry point для Void CRM MCP Server.
 *
 * Запуск:
 *   VOID_API_URL=http://localhost:8000/api/v1 \
 *   VOID_API_KEY=your-openrouter-api-key \
 *   node dist/index.js
 */

import { loadConfig } from "./config.js";
import { VoidCRMServer } from "./server.js";

async function main(): Promise<void> {
  try {
    const config = loadConfig();
    const server = new VoidCRMServer(config);
    await server.run();
  } catch (error) {
    console.error("Failed to start MCP server:", error);
    process.exit(1);
  }
}

main();
