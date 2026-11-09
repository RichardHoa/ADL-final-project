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
EMBED_BATCH_SIZE = 16

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

    def ingest(self, path, progress=None):
        progress = progress or (lambda stage, done=0, total=0: None)
        name = path.name
        progress("reading pages")
        pages = load_pages(path)
        progress("chunking")
        chunks = chunk_pages(name, pages)
        embeddings = []
        progress("embedding", 0, len(chunks))
        for start in range(0, len(chunks), EMBED_BATCH_SIZE):
            batch = chunks[start : start + EMBED_BATCH_SIZE]
            embeddings += self._ollama.embed([DOCUMENT_PREFIX + chunk.text for chunk in batch])
            progress("embedding", len(embeddings), len(chunks))
        progress("storing", len(chunks), len(chunks))
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
            count = collection.count()
            if count == 0:
                return []
            result = collection.query(
                query_embeddings=[embedding],
                n_results=min(top_k, count),
                include=["documents", "metadatas", "distances"],
            )
        return [
            {**self._record(chunk_id, text, metadata), "similarity": max(0.0, 1 - distance)}
            for chunk_id, text, metadata, distance in zip(
                result["ids"][0], result["documents"][0], result["metadatas"][0], result["distances"][0]
            )
        ]

    def chunks(self):
        with _lock:
            result = self._collection().get(include=["documents", "metadatas"])
        records = [
            self._record(chunk_id, text, metadata)
            for chunk_id, text, metadata in zip(result["ids"], result["documents"], result["metadatas"])
        ]
        return sorted(records, key=lambda record: (record["document"], record["index"]))

    def documents(self):
        with _lock:
            metadatas = self._collection().get(include=["metadatas"])["metadatas"]
        counts = Counter(metadata["source"] for metadata in metadatas)
        return [{"name": name, "chunks": count} for name, count in sorted(counts.items())]

    @staticmethod
    def _chunk_id(name, index):
        return f"{hashlib.sha1(name.encode()).hexdigest()}-{index}"

    @staticmethod
    def _record(chunk_id, text, metadata):
        index = int(chunk_id.rsplit("-", 1)[1])
        return {"document": metadata["source"], "page": metadata["page"], "index": index, "text": text}
