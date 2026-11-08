from pathlib import Path

from pypdf import PdfReader

SUPPORTED_EXTENSIONS = {".pdf", ".txt"}


class UnsupportedDocument(ValueError):
    pass


def is_supported(path):
    return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS


def load_pages(path):
    path = Path(path)
    extension = path.suffix.lower()
    if extension == ".pdf":
        reader = PdfReader(path)
        return [(number, page.extract_text() or "") for number, page in enumerate(reader.pages, start=1)]
    if extension == ".txt":
        return [(1, path.read_text(encoding="utf-8", errors="replace"))]
    raise UnsupportedDocument(f"Unsupported file type: {extension or path.name}. Use PDF or TXT.")
