import re
from dataclasses import dataclass

CHUNK_SIZE = 800
CHUNK_OVERLAP = 150


@dataclass(frozen=True)
class Chunk:
    source: str
    page: int
    text: str


def _split(text, separator_pattern):
    return [part for part in re.split(separator_pattern, text) if part.strip()]


def _pieces(text, size):
    if len(text) <= size:
        return [text]
    for pattern in (r"\n\s*\n", r"(?<=[.!?])\s+", r"\s+"):
        parts = _split(text, pattern)
        if len(parts) > 1:
            return [piece for part in parts for piece in _pieces(part.strip(), size)]
    return [text[i : i + size] for i in range(0, len(text), size)]


def _tail(text, overlap):
    if len(text) <= overlap:
        return text
    cut = text[-overlap:]
    space = cut.find(" ")
    return cut[space + 1 :] if space != -1 else cut


def split_text(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks = []
    current = ""
    for piece in _pieces(text.strip(), size - overlap):
        candidate = f"{current} {piece}".strip() if current else piece
        if len(candidate) <= size:
            current = candidate
            continue
        chunks.append(current)
        current = f"{_tail(current, overlap)} {piece}".strip()
    if current:
        chunks.append(current)
    return chunks


def chunk_pages(source, pages, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    return [
        Chunk(source=source, page=page, text=text)
        for page, page_text in pages
        for text in split_text(page_text, size, overlap)
    ]
