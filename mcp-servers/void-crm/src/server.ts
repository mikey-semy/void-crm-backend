/**
 * MCP Server для Void CRM.
 *
 * Предоставляет tools для работы с CRM через Claude Code.
 * Модульная структура позволяет расширять функционал.
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  type Tool,
} from "@modelcontextprotocol/sdk/types.js";

import type { Config } from "./config.js";
import { VoidApiClient } from "./api/client.js";
import {
  KNOWLEDGE_TOOLS,
  handleKnowledgeTool,
  isKnowledgeTool,
} from "./tools/knowledge.js";

// ==================== ALL TOOLS ====================

/**
 * Собирает все tools из всех доменов.
 */
function getAllTools(): Tool[] {
  return [
    ...KNOWLEDGE_TOOLS,
    // Будущие домены:
    // ...TASKS_TOOLS,
    // ...CHECKLIST_TOOLS,
    // ...CLIENTS_TOOLS,
  ];
}

// ==================== MCP SERVER ====================

export class VoidCRMServer {
  private server: Server;
  private client: VoidApiClient;

  constructor(config: Config) {
    this.client = new VoidApiClient(config);

    this.server = new Server(
      {
        name: "void-crm",
        version: "1.0.0",
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.setupHandlers();
  }

  private setupHandlers(): void {
    // List available tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: getAllTools(),
    }));

    // Handle tool calls
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        const result = await this.handleToolCall(name, args || {});
        return {
          content: [
            {
              type: "text",
              text: typeof result === "string" ? result : JSON.stringify(result, null, 2),
            },
          ],
        };
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : String(error);
        return {
          content: [
            {
              type: "text",
              text: `Error: ${errorMessage}`,
            },
          ],
          isError: true,
        };
      }
    });
  }

  private async handleToolCall(
    name: string,
    args: Record<string, unknown>
  ): Promise<unknown> {
    // Knowledge Base tools
    if (isKnowledgeTool(name)) {
      const result = await handleKnowledgeTool(name, args, this.client);
      if (result !== null) return result;
    }

    // Будущие домены:
    // if (isTasksTool(name)) {
    //   const result = await handleTasksTool(name, args, this.client);
    //   if (result !== null) return result;
    // }

    throw new Error(`Unknown tool: ${name}`);
  }

  async run(): Promise<void> {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error("Void CRM MCP Server running on stdio");
  }
}
