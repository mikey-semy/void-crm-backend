/**
 * HTTP клиент для взаимодействия с Void CRM API.
 */

import type { Config } from "../config.js";

// ==================== TYPES ====================

export interface MCPSearchRequest {
  query: string;
  category_id?: string;
  limit?: number;
  use_semantic?: boolean;
}

export interface MCPArticleSnippet {
  id: string;
  title: string;
  slug: string;
  description: string | null;
  category_name: string | null;
  tags: string[];
  relevance_score: number | null;
}

export interface MCPSearchResponse {
  success: boolean;
  query: string;
  total: number;
  articles: MCPArticleSnippet[];
}

export interface MCPArticleContent {
  id: string;
  title: string;
  slug: string;
  description: string | null;
  content: string;
  category_name: string | null;
  tags: string[];
  author: string;
  created_at: string;
  updated_at: string;
}

export interface MCPArticleResponse {
  success: boolean;
  article: MCPArticleContent;
}

export interface MCPCategoryItem {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  icon: string | null;
  articles_count: number;
}

export interface MCPCategoriesResponse {
  success: boolean;
  categories: MCPCategoryItem[];
}

export interface MCPTagItem {
  id: string;
  name: string;
  slug: string;
  articles_count: number;
}

export interface MCPTagsResponse {
  success: boolean;
  tags: MCPTagItem[];
}

export interface MCPSnippetItem {
  article_id: string;
  article_title: string;
  article_slug: string;
  language: string;
  code: string;
}

export interface MCPSnippetsResponse {
  success: boolean;
  tag: string;
  snippets: MCPSnippetItem[];
}

export interface MCPCreateArticleRequest {
  title: string;
  content: string;
  description?: string;
  category_id?: string;
  tag_ids?: string[];
  is_published?: boolean;
}

export interface MCPUpdateArticleRequest {
  title?: string;
  content?: string;
  description?: string;
  category_id?: string;
  tag_ids?: string[];
  is_published?: boolean;
}

export interface MCPSuccessResponse {
  success: boolean;
  message: string;
}

export interface MCPIndexResponse {
  success: boolean;
  message: string;
  indexed_count: number;
}

// ==================== CLIENT ====================

export class VoidApiClient {
  private config: Config;

  constructor(config: Config) {
    this.config = config;
  }

  private async request<T>(
    method: string,
    path: string,
    body?: unknown
  ): Promise<T> {
    const url = `${this.config.apiUrl}${path}`;

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "X-API-Key": this.config.apiKey,
    };

    const options: RequestInit = {
      method,
      headers,
      signal: AbortSignal.timeout(this.config.timeout),
    };

    if (body) {
      options.body = JSON.stringify(body);
    }

    const response = await fetch(url, options);

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(
        `API request failed: ${response.status} ${response.statusText} - ${errorText}`
      );
    }

    return response.json() as Promise<T>;
  }

  // ==================== SEARCH ====================

  /**
   * Семантический поиск по базе знаний.
   */
  async search(params: MCPSearchRequest): Promise<MCPSearchResponse> {
    return this.request<MCPSearchResponse>(
      "POST",
      "/knowledge/mcp/search",
      params
    );
  }

  // ==================== ARTICLES ====================

  /**
   * Получить статью по slug.
   */
  async getArticle(slug: string): Promise<MCPArticleResponse> {
    return this.request<MCPArticleResponse>(
      "GET",
      `/knowledge/mcp/article/${encodeURIComponent(slug)}`
    );
  }

  /**
   * Создать статью.
   */
  async createArticle(
    data: MCPCreateArticleRequest
  ): Promise<MCPArticleResponse> {
    return this.request<MCPArticleResponse>(
      "POST",
      "/knowledge/mcp/articles",
      data
    );
  }

  /**
   * Обновить статью.
   */
  async updateArticle(
    id: string,
    data: MCPUpdateArticleRequest
  ): Promise<MCPArticleResponse> {
    return this.request<MCPArticleResponse>(
      "PUT",
      `/knowledge/mcp/articles/${id}`,
      data
    );
  }

  /**
   * Удалить статью.
   */
  async deleteArticle(id: string): Promise<MCPSuccessResponse> {
    return this.request<MCPSuccessResponse>(
      "DELETE",
      `/knowledge/mcp/articles/${id}`
    );
  }

  /**
   * Найти похожие статьи.
   */
  async getSimilarArticles(
    id: string,
    limit: number = 5
  ): Promise<MCPSearchResponse> {
    return this.request<MCPSearchResponse>(
      "GET",
      `/knowledge/mcp/similar/${id}?limit=${limit}`
    );
  }

  // ==================== CATEGORIES & TAGS ====================

  /**
   * Получить список категорий.
   */
  async getCategories(): Promise<MCPCategoriesResponse> {
    return this.request<MCPCategoriesResponse>(
      "GET",
      "/knowledge/mcp/categories"
    );
  }

  /**
   * Получить популярные теги.
   */
  async getTags(limit: number = 20): Promise<MCPTagsResponse> {
    return this.request<MCPTagsResponse>(
      "GET",
      `/knowledge/mcp/tags?limit=${limit}`
    );
  }

  // ==================== SNIPPETS ====================

  /**
   * Получить сниппеты кода по тегу.
   */
  async getSnippets(
    tag: string,
    limit: number = 20
  ): Promise<MCPSnippetsResponse> {
    return this.request<MCPSnippetsResponse>(
      "GET",
      `/knowledge/mcp/snippets?tag=${encodeURIComponent(tag)}&limit=${limit}`
    );
  }

  // ==================== INDEXING ====================

  /**
   * Индексировать статьи для RAG.
   */
  async indexArticles(): Promise<MCPIndexResponse> {
    return this.request<MCPIndexResponse>("POST", "/knowledge/mcp/index");
  }
}
