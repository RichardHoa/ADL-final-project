import re
from dataclasses import dataclass

CHUNK_SIZE = 800
CHUNK_OVERLAP = 150

# Headings: numbered sections ("5.", "5.2", "5.2.2"), course descriptions ("CS302: ...", "CS 401/402: ..."),
# and appendices. A single-level number needs its dot, so table cells like "2 ELECTIVES" don't count.
SECTION_HEADING = re.compile(r"(\d+\.(?:\d+\.?)*)\s+(.+)")
COURSE_HEADING = re.compile(r"[A-Z]{2,4} ?\d(?:\d\d|xx)(?:/\d{3})?: .+")
APPENDIX_HEADING = re.compile(r"APPENDIX [IVX]+")
COURSE_LEVEL = 10
MAX_HEADING_LENGTH = 100
# Words a title leaves lowercase; any other lowercase word marks a numbered sentence, not a heading.
MINOR_WORDS = frozenset("a an and as at by for in of on or the to with".split())


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


def _is_title(text):
    words = re.findall(r"[A-Za-z][\w'’-]*", text)
    return bool(words) and all(word[0].isupper() or word.lower() in MINOR_WORDS for word in words)


def heading_level(line):
    """How deep a heading line sits (1 for "5.", 2 for "5.2", ...; course headings below every section), or None."""
    if ".." in line or len(line) > MAX_HEADING_LENGTH:
        return None
    if APPENDIX_HEADING.fullmatch(line):
        return 1
    if COURSE_HEADING.fullmatch(line):
        return COURSE_LEVEL
    match = SECTION_HEADING.fullmatch(line)
    if match and _is_title(match[2]):
        return match[1].rstrip(".").count(".") + 1
    return None


def _sections(pages):
    """(page, heading path, body) for each run of text between headings. Headings carry over to later pages."""
    headings = []
    for page, page_text in pages:
        body = []
        for line in page_text.splitlines():
            line = line.strip()
            level = heading_level(line)
            if level is None:
                body.append(line)
                continue
            yield page, headings, "\n".join(body).strip()
            body = []
            headings = [(depth, title) for depth, title in headings if depth < level] + [(level, line)]
        yield page, headings, "\n".join(body).strip()


def chunk_pages(source, pages, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Chunks of each page, each prefixed with the headings it sits under so retrieval sees its context."""
    chunks = []
    for page, headings, body in _sections(pages):
        if not body:
            continue
        prefix = " > ".join(title for _, title in headings)
        chunks += [
            Chunk(source=source, page=page, text=f"{prefix}\n{text}" if prefix else text)
            for text in split_text(body, size, overlap)
        ]
    return chunks
