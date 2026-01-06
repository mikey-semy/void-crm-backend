/**
 * Knowledge Base tools для MCP сервера.
 */

import type { Tool } from "@modelcontextprotocol/sdk/types.js";
import type { VoidApiClient } from "../api/client.js";

// ==================== TOOL DEFINITIONS ====================

export const KNOWLEDGE_TOOLS: Tool[] = [
  {
    name: "search_knowledge",
    description:
      "Search the Void CRM knowledge base using semantic (RAG) or full-text search. " +
      "Returns relevant articles based on the query. Use this to find documentation, " +
      "code examples, and best practices.",
    inputSchema: {
      type: "object",
      properties: {
        query: {
          type: "string",
          description: "Search query (2-500 characters)",
        },
        category_id: {
          type: "string",
          description: "Optional category ID to filter results",
        },
        limit: {
          type: "number",
          description: "Maximum number of results (1-50, default 10)",
          default: 10,
        },
        use_semantic: {
          type: "boolean",
          description: "Use semantic search (RAG) instead of full-text search",
          default: true,
        },
      },
      required: ["query"],
    },
  },
  {
    name: "read_article",
    description:
      "Read the full content of a knowledge base article by its slug. " +
      "Returns the complete Markdown content, metadata, and tags.",
    inputSchema: {
      type: "object",
      properties: {
        slug: {
          type: "string",
          description: "URL-friendly article identifier (slug)",
        },
      },
      required: ["slug"],
    },
  },
  {
    name: "list_categories",
    description:
      "List all categories in the knowledge base with article counts. " +
      "Use this to discover available documentation sections.",
    inputSchema: {
      type: "object",
      properties: {},
    },
  },
  {
    name: "list_tags",
    description:
      "List popular tags in the knowledge base with article counts. " +
      "Use this to find articles by technology or topic.",
    inputSchema: {
      type: "object",
      properties: {
        limit: {
          type: "number",
          description: "Maximum number of tags to return (default 20)",
          default: 20,
        },
      },
    },
  },
  {
    name: "get_snippets",
    description:
      "Get code snippets from articles with a specific tag. " +
      "Returns extracted code blocks with their language and source article.",
    inputSchema: {
      type: "object",
      properties: {
        tag: {
          type: "string",
          description: "Tag slug to filter snippets (e.g., 'typescript', 'docker')",
        },
        limit: {
          type: "number",
          description: "Maximum number of snippets to return (default 20)",
          default: 20,
        },
      },
      required: ["tag"],
    },
  },
  {
    name: "create_article",
    description:
      "Create a new article in the knowledge base. " +
      "The article will be saved as a draft by default.",
    inputSchema: {
      type: "object",
      properties: {
        title: {
          type: "string",
          description: "Article title (3-500 characters)",
        },
        content: {
          type: "string",
          description: "Article content in Markdown format",
        },
        description: {
          type: "string",
          description: "Short description for previews (optional)",
        },
        category_id: {
          type: "string",
          description: "Category ID (optional)",
        },
        tag_ids: {
          type: "array",
          items: { type: "string" },
          description: "List of tag IDs (optional)",
        },
        is_published: {
          type: "boolean",
          description: "Publish immediately (default false)",
          default: false,
        },
      },
      required: ["title", "content"],
    },
  },
  {
    name: "update_article",
    description:
      "Update an existing article in the knowledge base. " +
      "Only provided fields will be updated.",
    inputSchema: {
      type: "object",
      properties: {
        id: {
          type: "string",
          description: "Article UUID",
        },
        title: {
          type: "string",
          description: "New title (optional)",
        },
        content: {
          type: "string",
          description: "New content in Markdown (optional)",
        },
        description: {
          type: "string",
          description: "New description (optional)",
        },
        category_id: {
          type: "string",
          description: "New category ID (optional)",
        },
        tag_ids: {
          type: "array",
          items: { type: "string" },
          description: "New list of tag IDs (optional)",
        },
        is_published: {
          type: "boolean",
          description: "Publish/unpublish (optional)",
        },
      },
      required: ["id"],
    },
  },
  {
    name: "delete_article",
    description: "Delete an article from the knowledge base.",
    inputSchema: {
      type: "object",
      properties: {
        id: {
          type: "string",
          description: "Article UUID to delete",
        },
      },
      required: ["id"],
    },
  },
  {
    name: "find_similar",
    description:
      "Find articles similar to a given article using semantic search. " +
      "Useful for discovering related documentation.",
    inputSchema: {
      type: "object",
      properties: {
        id: {
          type: "string",
          description: "Source article UUID",
        },
        limit: {
          type: "number",
          description: "Maximum number of similar articles (default 5)",
          default: 5,
        },
      },
      required: ["id"],
    },
  },
  {
    name: "index_articles",
    description:
      "Re-index all articles for semantic search (RAG). " +
      "Run this after adding multiple articles to enable semantic search.",
    inputSchema: {
      type: "object",
      properties: {},
    },
  },
];

// ==================== TOOL HANDLERS ====================

export async function handleKnowledgeTool(
  name: string,
  args: Record<string, unknown>,
  client: VoidApiClient
): Promise<unknown> {
  switch (name) {
    case "search_knowledge": {
      const response = await client.search({
        query: args.query as string,
        category_id: args.category_id as string | undefined,
        limit: (args.limit as number) || 10,
        use_semantic: args.use_semantic !== false,
      });

      if (response.articles.length === 0) {
        return `No articles found for query: "${response.query}"`;
      }

      const articleList = response.articles
        .map(
          (a, i) =>
            `${i + 1}. **${a.title}**\n` +
            `   Slug: ${a.slug}\n` +
            `   ${a.description || "No description"}\n` +
            `   Tags: ${a.tags.join(", ") || "none"}`
        )
        .join("\n\n");

      return `Found ${response.total} articles for "${response.query}":\n\n${articleList}`;
    }

    case "read_article": {
      const response = await client.getArticle(args.slug as string);
      const article = response.article;

      return (
        `# ${article.title}\n\n` +
        `**Category:** ${article.category_name || "Uncategorized"}\n` +
        `**Tags:** ${article.tags.join(", ") || "none"}\n` +
        `**Author:** ${article.author}\n` +
        `**Updated:** ${article.updated_at}\n\n` +
        `---\n\n` +
        `${article.content}`
      );
    }

    case "list_categories": {
      const response = await client.getCategories();

      if (response.categories.length === 0) {
        return "No categories found.";
      }

      const categoryList = response.categories
        .map(
          (c) =>
            `- **${c.name}** (${c.slug}): ${c.articles_count} articles\n` +
            `  ${c.description || "No description"}`
        )
        .join("\n");

      return `Knowledge Base Categories:\n\n${categoryList}`;
    }

    case "list_tags": {
      const response = await client.getTags((args.limit as number) || 20);

      if (response.tags.length === 0) {
        return "No tags found.";
      }

      const tagList = response.tags
        .map((t) => `- **${t.name}** (${t.slug}): ${t.articles_count} articles`)
        .join("\n");

      return `Popular Tags:\n\n${tagList}`;
    }

    case "get_snippets": {
      const response = await client.getSnippets(
        args.tag as string,
        (args.limit as number) || 20
      );

      if (response.snippets.length === 0) {
        return `No code snippets found for tag: "${response.tag}"`;
      }

      const snippetList = response.snippets
        .map(
          (s) =>
            `### From: ${s.article_title}\n\n` +
            `\`\`\`${s.language}\n${s.code}\n\`\`\``
        )
        .join("\n\n---\n\n");

      return `Code snippets for tag "${response.tag}":\n\n${snippetList}`;
    }

    case "create_article": {
      const response = await client.createArticle({
        title: args.title as string,
        content: args.content as string,
        description: args.description as string | undefined,
        category_id: args.category_id as string | undefined,
        tag_ids: args.tag_ids as string[] | undefined,
        is_published: (args.is_published as boolean) || false,
      });

      const article = response.article;
      return (
        `Article created successfully!\n\n` +
        `**Title:** ${article.title}\n` +
        `**ID:** ${article.id}\n` +
        `**Slug:** ${article.slug}\n` +
        `**Status:** ${args.is_published ? "Published" : "Draft"}`
      );
    }

    case "update_article": {
      const { id, ...updateData } = args as { id: string } & Record<string, unknown>;
      const response = await client.updateArticle(id, updateData);

      const article = response.article;
      return (
        `Article updated successfully!\n\n` +
        `**Title:** ${article.title}\n` +
        `**ID:** ${article.id}\n` +
        `**Slug:** ${article.slug}`
      );
    }

    case "delete_article": {
      const response = await client.deleteArticle(args.id as string);
      return response.message;
    }

    case "find_similar": {
      const response = await client.getSimilarArticles(
        args.id as string,
        (args.limit as number) || 5
      );

      if (response.articles.length === 0) {
        return "No similar articles found.";
      }

      const articleList = response.articles
        .map(
          (a, i) =>
            `${i + 1}. **${a.title}**\n` +
            `   Slug: ${a.slug}\n` +
            `   ${a.description || "No description"}`
        )
        .join("\n\n");

      return `Similar articles:\n\n${articleList}`;
    }

    case "index_articles": {
      const response = await client.indexArticles();
      return `${response.message}\nIndexed ${response.indexed_count} articles.`;
    }

    default:
      return null; // Not handled by this module
  }
}

/**
 * Проверяет, является ли tool частью Knowledge домена.
 */
export function isKnowledgeTool(name: string): boolean {
  return KNOWLEDGE_TOOLS.some((t) => t.name === name);
}
