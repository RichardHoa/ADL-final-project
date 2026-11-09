import hashlib
import math
import threading
from collections import Counter

import chromadb
from chromadb.config import Settings

from rag.ingestion.chunker import chunk_pages
from rag.ingestion.loader import load_pages
from rag.retrieval.keyword import keyword_scores

DOCUMENT_PREFIX = "search_document: "
QUERY_PREFIX = "search_query: "
COLLECTION_NAME = "chunks"
EMBED_BATCH_SIZE = 16
CANDIDATE_K = 20
DENSE_WEIGHT = 0.6
KEYWORD_WEIGHT = 0.4

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

    def search(self, question, top_k, min_score=0.0):
        """The top_k Chunks by hybrid score, dropping any below min_score."""
        candidates = [chunk for chunk in self.candidates(question, top_k) if chunk["score"] >= min_score]
        return candidates[:top_k]

    def candidates(self, question, pool_size=CANDIDATE_K):
        """Union of the dense and keyword top pool_size (at least CANDIDATE_K) Chunks, each scored, best first."""
        pool_size = max(pool_size, CANDIDATE_K)
        embedding = self._ollama.embed([QUERY_PREFIX + question])[0]
        with _lock:
            collection = self._collection()
            count = collection.count()
            if count == 0:
                return []
            stored = collection.get(include=["documents", "metadatas"])
            dense = collection.query(
                query_embeddings=[embedding], n_results=min(pool_size, count), include=["distances"]
            )
            similarities = {
                chunk_id: max(0.0, 1 - distance) for chunk_id, distance in zip(dense["ids"][0], dense["distances"][0])
            }
            keywords = dict(zip(stored["ids"], keyword_scores(question, stored["documents"])))
            keyword_top = sorted((chunk_id for chunk_id in keywords if keywords[chunk_id] > 0), key=keywords.get, reverse=True)
            missing = [chunk_id for chunk_id in keyword_top[:pool_size] if chunk_id not in similarities]
            if missing:
                fetched = collection.get(ids=missing, include=["embeddings"])
                for chunk_id, vector in zip(fetched["ids"], fetched["embeddings"]):
                    similarities[chunk_id] = max(0.0, _cosine(embedding, vector))
        texts = dict(zip(stored["ids"], zip(stored["documents"], stored["metadatas"])))
        results = [
            {
                **self._record(chunk_id, *texts[chunk_id]),
                "score": DENSE_WEIGHT * similarity + KEYWORD_WEIGHT * keywords[chunk_id],
                "similarity": similarity,
                "keyword": keywords[chunk_id],
            }
            for chunk_id, similarity in similarities.items()
        ]
        return sorted(results, key=lambda result: result["score"], reverse=True)

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


def _cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0
