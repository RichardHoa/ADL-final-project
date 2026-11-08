import hashlib
import threading
from collections import Counter

import chromadb
from chromadb.config import Settings

from rag.ingestion.chunker import chunk_pages
from rag.ingestion.loader import load_pages

DOCUMENT_PREFIX = "search_document: "
QUERY_PREFIX = "search_query: "
COLLECTION_NAME = "chunks"

_lock = threading.Lock()


class KnowledgeBase:
    def __init__(self, path, ollama):
        self._path = str(path)
        self._ollama = ollama

    def _collection(self):
        settings = Settings(anonymized_telemetry=False)
        chromadb.PersistentClient(path=self._path, settings=settings).clear_system_cache()
        client = chromadb.PersistentClient(path=self._path, settings=settings)
        return client.get_or_create_collection(
            COLLECTION_NAME, embedding_function=None, metadata={"hnsw:space": "cosine"}
        )

    def ingest(self, path):
        name = path.name
        chunks = chunk_pages(name, load_pages(path))
        embeddings = self._ollama.embed([DOCUMENT_PREFIX + chunk.text for chunk in chunks]) if chunks else []
        with _lock:
            collection = self._collection()
            collection.delete(where={"source": name})
            if chunks:
                collection.add(
                    ids=[self._chunk_id(name, index) for index in range(len(chunks))],
                    embeddings=embeddings,
                    documents=[chunk.text for chunk in chunks],
                    metadatas=[{"source": chunk.source, "page": chunk.page} for chunk in chunks],
                )
        return {"name": name, "chunks": len(chunks)}

    def search(self, question, top_k):
        embedding = self._ollama.embed([QUERY_PREFIX + question])[0]
        with _lock:
            collection = self._collection()
            if collection.count() == 0:
                return []
            result = collection.query(query_embeddings=[embedding], n_results=top_k)
        return [
            {"source": metadata["source"], "page": metadata["page"], "text": text}
            for text, metadata in zip(result["documents"][0], result["metadatas"][0])
        ]

    def documents(self):
        with _lock:
            metadatas = self._collection().get(include=["metadatas"])["metadatas"]
        counts = Counter(metadata["source"] for metadata in metadatas)
        return [{"name": name, "chunks": count} for name, count in sorted(counts.items())]

    @staticmethod
    def _chunk_id(name, index):
        return f"{hashlib.sha1(name.encode()).hexdigest()}-{index}"
