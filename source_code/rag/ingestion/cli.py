import argparse
from pathlib import Path

from rag.ingestion.loader import is_supported
from rag.services import build_services


def find_documents(path):
    if path.is_dir():
        return sorted(file for file in path.iterdir() if file.is_file() and is_supported(file))
    return [path] if path.is_file() and is_supported(path) else []


def main(argv=None, storage_dir=None, ollama=None):
    parser = argparse.ArgumentParser(description="Ingest PDF and TXT Documents into the knowledge base.")
    parser.add_argument("path", type=Path, help="A Document or a folder of Documents")
    args = parser.parse_args(argv)

    knowledge_base = build_services(storage_dir, ollama).knowledge_base
    documents = find_documents(args.path)
    if not documents:
        print(f"No PDF or TXT Documents found in {args.path}")
        return 1
    for document in documents:
        result = knowledge_base.ingest(document)
        print(f"{result['name']}: {result['chunks']} chunks")
    print(f"Ingested {len(documents)} document(s).")
    return 0
