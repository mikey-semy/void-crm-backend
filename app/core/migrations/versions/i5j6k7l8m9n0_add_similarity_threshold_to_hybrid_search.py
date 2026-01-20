"""add similarity_threshold to hybrid_search function

Revision ID: i5j6k7l8m9n0
Revises: h4i5j6k7l8m9
Create Date: 2026-01-20 15:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "i5j6k7l8m9n0"
down_revision: Union[str, Sequence[str], None] = "h4i5j6k7l8m9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Обновляем функцию гибридного поиска с добавлением similarity_threshold
    op.execute("""
        CREATE OR REPLACE FUNCTION hybrid_search(
            query_text TEXT,
            query_embedding vector(1536),
            match_count INT DEFAULT 20,
            full_text_weight FLOAT DEFAULT 1.0,
            semantic_weight FLOAT DEFAULT 1.0,
            rrf_k INT DEFAULT 60,
            category_filter UUID DEFAULT NULL,
            similarity_threshold FLOAT DEFAULT 0.3
        )
        RETURNS TABLE (
            id UUID,
            fts_rank FLOAT,
            semantic_rank FLOAT,
            combined_score FLOAT
        )
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RETURN QUERY
            WITH fts_results AS (
                -- Полнотекстовый поиск с ранжированием
                SELECT
                    ka.id AS article_id,
                    ROW_NUMBER() OVER (
                        ORDER BY ts_rank(ka.search_vector, plainto_tsquery('russian', query_text)) DESC
                    )::INT AS rank_ix,
                    ts_rank(ka.search_vector, plainto_tsquery('russian', query_text))::FLOAT AS fts_score
                FROM knowledge_articles ka
                WHERE ka.is_published = true
                    AND ka.search_vector @@ plainto_tsquery('russian', query_text)
                    AND (category_filter IS NULL OR ka.category_id = category_filter)
                ORDER BY fts_score DESC
                LIMIT match_count * 2
            ),
            semantic_results AS (
                -- Семантический поиск с ранжированием и threshold
                SELECT
                    ka.id AS article_id,
                    ROW_NUMBER() OVER (
                        ORDER BY ka.embedding <=> query_embedding
                    )::INT AS rank_ix,
                    (1 - (ka.embedding <=> query_embedding))::FLOAT AS semantic_score
                FROM knowledge_articles ka
                WHERE ka.is_published = true
                    AND ka.embedding IS NOT NULL
                    AND (category_filter IS NULL OR ka.category_id = category_filter)
                    -- Фильтруем по threshold: cosine_distance < (1 - similarity_threshold)
                    AND (ka.embedding <=> query_embedding) < (1 - similarity_threshold)
                ORDER BY ka.embedding <=> query_embedding
                LIMIT match_count * 2
            ),
            combined AS (
                -- RRF слияние результатов
                SELECT
                    COALESCE(fts.article_id, sem.article_id) AS article_id,
                    COALESCE(fts.fts_score, 0)::FLOAT AS fts_score,
                    COALESCE(sem.semantic_score, 0)::FLOAT AS semantic_score,
                    -- RRF формула
                    (
                        (1.0 / (rrf_k + COALESCE(fts.rank_ix, match_count * 2 + 1))) * full_text_weight +
                        (1.0 / (rrf_k + COALESCE(sem.rank_ix, match_count * 2 + 1))) * semantic_weight
                    )::FLOAT AS combined_score
                FROM fts_results fts
                FULL OUTER JOIN semantic_results sem ON fts.article_id = sem.article_id
            )
            SELECT
                c.article_id AS id,
                c.fts_score AS fts_rank,
                c.semantic_score AS semantic_rank,
                c.combined_score
            FROM combined c
            ORDER BY c.combined_score DESC
            LIMIT match_count;
        END;
        $$;
    """)

    # Обновляем комментарий к функции
    op.execute("""
        COMMENT ON FUNCTION hybrid_search IS
        'Гибридный поиск с RRF (Reciprocal Rank Fusion) для комбинирования
        полнотекстового и семантического поиска.
        Параметры:
        - query_text: текстовый запрос для FTS
        - query_embedding: вектор запроса для семантического поиска
        - match_count: количество результатов (default 20)
        - full_text_weight: вес FTS (default 1.0)
        - semantic_weight: вес семантического поиска (default 1.0)
        - rrf_k: параметр RRF, влияет на сглаживание (default 60)
        - category_filter: фильтр по категории (optional)
        - similarity_threshold: минимальный порог схожести 0-1 (default 0.3)';
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Возвращаем старую версию функции без threshold
    op.execute("""
        CREATE OR REPLACE FUNCTION hybrid_search(
            query_text TEXT,
            query_embedding vector(1536),
            match_count INT DEFAULT 20,
            full_text_weight FLOAT DEFAULT 1.0,
            semantic_weight FLOAT DEFAULT 1.0,
            rrf_k INT DEFAULT 60,
            category_filter UUID DEFAULT NULL
        )
        RETURNS TABLE (
            id UUID,
            fts_rank FLOAT,
            semantic_rank FLOAT,
            combined_score FLOAT
        )
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RETURN QUERY
            WITH fts_results AS (
                SELECT
                    ka.id AS article_id,
                    ROW_NUMBER() OVER (
                        ORDER BY ts_rank(ka.search_vector, plainto_tsquery('russian', query_text)) DESC
                    )::INT AS rank_ix,
                    ts_rank(ka.search_vector, plainto_tsquery('russian', query_text))::FLOAT AS fts_score
                FROM knowledge_articles ka
                WHERE ka.is_published = true
                    AND ka.search_vector @@ plainto_tsquery('russian', query_text)
                    AND (category_filter IS NULL OR ka.category_id = category_filter)
                ORDER BY fts_score DESC
                LIMIT match_count * 2
            ),
            semantic_results AS (
                SELECT
                    ka.id AS article_id,
                    ROW_NUMBER() OVER (
                        ORDER BY ka.embedding <=> query_embedding
                    )::INT AS rank_ix,
                    (1 - (ka.embedding <=> query_embedding))::FLOAT AS semantic_score
                FROM knowledge_articles ka
                WHERE ka.is_published = true
                    AND ka.embedding IS NOT NULL
                    AND (category_filter IS NULL OR ka.category_id = category_filter)
                ORDER BY ka.embedding <=> query_embedding
                LIMIT match_count * 2
            ),
            combined AS (
                SELECT
                    COALESCE(fts.article_id, sem.article_id) AS article_id,
                    COALESCE(fts.fts_score, 0)::FLOAT AS fts_score,
                    COALESCE(sem.semantic_score, 0)::FLOAT AS semantic_score,
                    (
                        (1.0 / (rrf_k + COALESCE(fts.rank_ix, match_count * 2 + 1))) * full_text_weight +
                        (1.0 / (rrf_k + COALESCE(sem.rank_ix, match_count * 2 + 1))) * semantic_weight
                    )::FLOAT AS combined_score
                FROM fts_results fts
                FULL OUTER JOIN semantic_results sem ON fts.article_id = sem.article_id
            )
            SELECT
                c.article_id AS id,
                c.fts_score AS fts_rank,
                c.semantic_score AS semantic_rank,
                c.combined_score
            FROM combined c
            ORDER BY c.combined_score DESC
            LIMIT match_count;
        END;
        $$;
    """)
