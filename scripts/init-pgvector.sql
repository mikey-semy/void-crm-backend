-- Инициализация pgvector расширения для PostgreSQL
-- Этот скрипт выполняется автоматически при первом запуске контейнера

-- Создать расширение vector для работы с векторными эмбеддингами
CREATE EXTENSION IF NOT EXISTS vector;

-- Проверка установленных расширений
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';

-- Примечание:
-- После установки можно создавать колонки типа vector(N), например:
-- CREATE TABLE documents (id UUID, embedding vector(1536));
-- SELECT * FROM documents ORDER BY embedding <=> '[0.1, 0.2, ...]'::vector LIMIT 10;
