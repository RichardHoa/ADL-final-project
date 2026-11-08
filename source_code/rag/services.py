from dataclasses import dataclass
from pathlib import Path

from rag.config import load_config
from rag.conversations.store import ConversationStore
from rag.ollama_client import OllamaClient
from rag.retrieval.knowledge_base import KnowledgeBase


@dataclass(frozen=True)
class Services:
    ollama: object
    knowledge_base: KnowledgeBase
    conversations: ConversationStore
    uploads_dir: Path
    top_k: int


def build_services(storage_dir=None, ollama=None, top_k=None):
    config = load_config()
    storage_dir = Path(storage_dir or config.storage_dir)
    uploads_dir = storage_dir / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    ollama = ollama or OllamaClient(config.ollama_host, config.embed_model, config.llm_model)
    return Services(
        ollama=ollama,
        knowledge_base=KnowledgeBase(storage_dir / "chroma", ollama),
        conversations=ConversationStore(storage_dir / "chat.db"),
        uploads_dir=uploads_dir,
        top_k=top_k or config.top_k,
    )
