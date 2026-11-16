import re
from bisect import bisect_right
from dataclasses import dataclass

# Most sections fit in one Chunk; longer ones are split, preferring paragraph breaks, then sentence ends,
# then line breaks, then any whitespace.
MAX_CHUNK_SIZE = 750
BOUNDARIES = [re.compile(pattern) for pattern in (r"\n\s*\n", r"(?<=[.!?])\s+", r"\n", r"\s+")]

# Headings: numbered sections ("5.", "5.2", "5.2.2"), course descriptions ("CS302: ...", "CS 401/402: ..."),
# and appendices. A single-level number needs its dot, so table cells like "2 ELECTIVES" don't count.
SECTION_HEADING = re.compile(r"(\d+\.(?:\d+\.?)*)\s+(.+)")
COURSE_HEADING = re.compile(r"[A-Z]{2,4} ?\d(?:\d\d|xx)(?:/\d{3})?: .+")
APPENDIX_HEADING = re.compile(r"APPENDIX [IVX]+")
# Table of contents entries ("Major Requirements (56 credits) ........ 7"). Their titles are the Document's headings,
# including unnumbered ones. The entries themselves repeat headings without their content, so they're dropped.
TABLE_OF_CONTENTS_LINE = re.compile(r"(.*?)\s*\.{4,}\s*\d+")
FOOTNOTE = re.compile(r"\s+\d+$")
COURSE_LEVEL = 10
MAX_HEADING_LENGTH = 100
# Words a title leaves lowercase; any other lowercase word marks a numbered sentence, not a heading.
MINOR_WORDS = frozenset("a an and as at by for in of on or the to with".split())


@dataclass(frozen=True)
class Chunk:
    source: str
    pages: tuple[int, ...]
    text: str


def _cut(window, size):
    """Where to end a piece within window: the last boundary of the most preferred kind, else size."""
    for boundary in BOUNDARIES:
        cuts = [match.start() for match in boundary.finditer(window) if match.start() > 0]
        if cuts:
            return cuts[-1]
    return size


def _pieces(text, size):
    """(offset, piece) for each piece of at most size characters, cut at the last boundary that fits, without overlap."""
    start = len(text) - len(text.lstrip())
    while len(text) - start > size:
        cut = _cut(text[start : start + size + 1], size)
        yield start, text[start : start + cut].rstrip()
        rest = text[start + cut :]
        start += cut + len(rest) - len(rest.lstrip())
    if text[start:].strip():
        yield start, text[start:].rstrip()


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


def _normalize(text):
    return " ".join(text.split())


def _table_of_contents(pages):
    """Heading level of each table of contents title. An unnumbered title sits one level below the numbered one above it."""
    levels = {}
    parent = 0
    for _, page_text in pages:
        for line in page_text.splitlines():
            match = TABLE_OF_CONTENTS_LINE.fullmatch(line.strip())
            if not match:
                continue
            title = _normalize(match[1])
            number = SECTION_HEADING.fullmatch(title)
            if number:
                parent = number[1].rstrip(".").count(".") + 1
                levels[title] = parent
            else:
                levels[title] = heading_level(title) or parent + 1
    return levels


def _heading(line, contents):
    """(level, title) if the line is a heading, else None. A table of contents title may carry a footnote number."""
    level = heading_level(line)
    if level is not None:
        return level, line
    line = _normalize(line)
    for title in (line, FOOTNOTE.sub("", line)):
        if title in contents:
            return contents[title], title
    return None


def _sections(pages):
    """(start page, heading path, (page, line) pairs) for each run of text between headings. Sections continue across
    pages; text before the first heading is a section with no headings."""
    contents = _table_of_contents(pages)
    headings = []
    start = None
    body = []
    for page, page_text in pages:
        for line in page_text.splitlines():
            line = line.strip()
            if TABLE_OF_CONTENTS_LINE.fullmatch(line):
                continue
            heading = _heading(line, contents)
            if heading is None:
                if start is None and line:
                    start = page
                body.append((page, line))
                continue
            yield start, headings, body
            start = page
            body = []
            headings = [(depth, title) for depth, title in headings if depth < heading[0]] + [heading]
    yield start, headings, body


def chunk_pages(source, pages, size=MAX_CHUNK_SIZE):
    """One Chunk per section, prefixed with the headings it sits under so retrieval sees its context. A section longer
    than size is split into pieces. Each Chunk lists every page its text spans: the first piece from the page the
    section starts on, the rest from the page they start on, through the page they end on."""
    chunks = []
    for start, headings, body in _sections(pages):
        text = "\n".join(line for _, line in body)
        line_starts = [0]
        for _, line in body:
            line_starts.append(line_starts[-1] + len(line) + 1)
        prefix = " > ".join(title for _, title in headings)
        for number, (offset, piece) in enumerate(_pieces(text, size)):
            first = start if number == 0 else body[bisect_right(line_starts, offset) - 1][0]
            last = body[bisect_right(line_starts, offset + len(piece) - 1) - 1][0]
            pages_spanned = tuple(range(first, last + 1))
            chunks.append(Chunk(source=source, pages=pages_spanned, text=f"{prefix}\n{piece}" if prefix else piece))
    return chunks
