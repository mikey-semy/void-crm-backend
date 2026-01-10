"""
Утилиты для разбиения текста на чанки для RAG.

Поддерживает разбиение Markdown документов на логические части
с сохранением контекста (заголовков секций).
"""

import re

from pydantic import BaseModel, Field


class TextChunkSchema(BaseModel):
    """Схема чанка текста с метаданными."""

    index: int = Field(description="Порядковый номер чанка")
    title: str | None = Field(None, description="Заголовок секции")
    content: str = Field(description="Содержимое чанка")
    token_count: int = Field(description="Приблизительное количество токенов")


# Приблизительное соотношение символов к токенам для русского/английского текста
CHARS_PER_TOKEN = 4

# Настройки чанкинга
DEFAULT_CHUNK_SIZE = 500  # токенов
DEFAULT_CHUNK_OVERLAP = 50  # токенов перекрытия
MIN_CHUNK_SIZE = 100  # минимальный размер чанка в токенах


def estimate_tokens(text: str) -> int:
    """
    Приблизительно оценивает количество токенов в тексте.

    Args:
        text: Исходный текст

    Returns:
        Приблизительное количество токенов
    """
    return len(text) // CHARS_PER_TOKEN


def split_markdown_by_headers(content: str) -> list[tuple[str | None, str]]:
    """
    Разбивает Markdown документ по заголовкам.

    Args:
        content: Markdown текст

    Returns:
        Список кортежей (заголовок, содержимое секции)
    """
    # Паттерн для заголовков Markdown (# ## ### и т.д.)
    header_pattern = r'^(#{1,6})\s+(.+)$'

    lines = content.split('\n')
    sections: list[tuple[str | None, str]] = []
    current_title: str | None = None
    current_content: list[str] = []

    for line in lines:
        header_match = re.match(header_pattern, line)
        if header_match:
            # Сохраняем предыдущую секцию
            if current_content:
                sections.append((current_title, '\n'.join(current_content).strip()))

            # Начинаем новую секцию
            current_title = header_match.group(2).strip()
            current_content = []
        else:
            current_content.append(line)

    # Сохраняем последнюю секцию
    if current_content:
        sections.append((current_title, '\n'.join(current_content).strip()))

    return sections


def split_text_into_chunks(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[str]:
    """
    Разбивает текст на чанки по размеру с перекрытием.

    Пытается разбивать по параграфам и предложениям, не по середине слова.

    Args:
        text: Исходный текст
        chunk_size: Желаемый размер чанка в токенах
        chunk_overlap: Размер перекрытия в токенах

    Returns:
        Список чанков текста
    """
    if not text.strip():
        return []

    target_chars = chunk_size * CHARS_PER_TOKEN
    overlap_chars = chunk_overlap * CHARS_PER_TOKEN

    # Разбиваем по параграфам
    paragraphs = re.split(r'\n\s*\n', text)

    chunks: list[str] = []
    current_chunk: list[str] = []
    current_size = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        para_size = len(para)

        # Если параграф слишком большой, разбиваем по предложениям
        if para_size > target_chars:
            # Сначала сохраняем накопленный чанк
            if current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                # Берём последний параграф для перекрытия
                if overlap_chars > 0 and current_chunk:
                    overlap_text = current_chunk[-1]
                    if len(overlap_text) > overlap_chars:
                        overlap_text = overlap_text[-overlap_chars:]
                    current_chunk = [overlap_text]
                    current_size = len(overlap_text)
                else:
                    current_chunk = []
                    current_size = 0

            # Разбиваем большой параграф по предложениям
            sentences = re.split(r'(?<=[.!?])\s+', para)
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue

                sentence_size = len(sentence)

                if current_size + sentence_size > target_chars and current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    if overlap_chars > 0:
                        overlap_text = ' '.join(current_chunk)[-overlap_chars:]
                        current_chunk = [overlap_text] if overlap_text else []
                        current_size = len(overlap_text)
                    else:
                        current_chunk = []
                        current_size = 0

                current_chunk.append(sentence)
                current_size += sentence_size

        # Если параграф помещается в чанк
        elif current_size + para_size <= target_chars:
            current_chunk.append(para)
            current_size += para_size
        else:
            # Сохраняем текущий чанк и начинаем новый
            if current_chunk:
                chunks.append('\n\n'.join(current_chunk))

            # Перекрытие
            if overlap_chars > 0 and current_chunk:
                overlap_text = current_chunk[-1]
                if len(overlap_text) > overlap_chars:
                    overlap_text = overlap_text[-overlap_chars:]
                current_chunk = [overlap_text, para]
                current_size = len(overlap_text) + para_size
            else:
                current_chunk = [para]
                current_size = para_size

    # Сохраняем последний чанк
    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))

    return chunks


def chunk_article(
    content: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[TextChunkSchema]:
    """
    Разбивает статью на чанки с сохранением контекста заголовков.

    Алгоритм:
    1. Сначала разбивает по заголовкам Markdown
    2. Если секция слишком большая, разбивает её на подчанки
    3. Каждый чанк сохраняет заголовок родительской секции

    Args:
        content: Содержимое статьи (Markdown)
        chunk_size: Желаемый размер чанка в токенах
        chunk_overlap: Размер перекрытия в токенах

    Returns:
        Список чанков с метаданными
    """
    if not content or not content.strip():
        return []

    # Разбиваем по заголовкам
    sections = split_markdown_by_headers(content)

    chunks: list[TextChunkSchema] = []
    chunk_index = 0

    for section_title, section_content in sections:
        if not section_content.strip():
            continue

        section_tokens = estimate_tokens(section_content)

        # Если секция помещается в один чанк
        if section_tokens <= chunk_size:
            chunks.append(TextChunkSchema(
                index=chunk_index,
                title=section_title,
                content=section_content.strip(),
                token_count=section_tokens,
            ))
            chunk_index += 1
        else:
            # Разбиваем большую секцию на подчанки
            sub_chunks = split_text_into_chunks(
                section_content,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
            for sub_content in sub_chunks:
                if sub_content.strip():
                    chunks.append(TextChunkSchema(
                        index=chunk_index,
                        title=section_title,
                        content=sub_content.strip(),
                        token_count=estimate_tokens(sub_content),
                    ))
                    chunk_index += 1

    # Фильтруем слишком маленькие чанки (объединяем с предыдущими)
    filtered_chunks: list[TextChunkSchema] = []
    for chunk in chunks:
        if chunk.token_count < MIN_CHUNK_SIZE and filtered_chunks:
            # Объединяем с предыдущим чанком
            prev = filtered_chunks[-1]
            combined_content = f"{prev.content}\n\n{chunk.content}"
            filtered_chunks[-1] = TextChunkSchema(
                index=prev.index,
                title=prev.title,
                content=combined_content,
                token_count=estimate_tokens(combined_content),
            )
        else:
            filtered_chunks.append(chunk)

    # Перенумеровываем
    for i, chunk in enumerate(filtered_chunks):
        filtered_chunks[i] = TextChunkSchema(
            index=i,
            title=chunk.title,
            content=chunk.content,
            token_count=chunk.token_count,
        )

    return filtered_chunks
