import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    ollama_host: str
    embed_model: str
    llm_model: str
    storage_dir: Path
    top_k: int
    min_score: float


def load_config():
    return Config(
        ollama_host=os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
        embed_model=os.environ.get("EMBED_MODEL", "nomic-embed-text"),
        llm_model=os.environ.get("LLM_MODEL", "qwen2.5:0.5b"),
        storage_dir=Path(os.environ.get("STORAGE_DIR", "storage")),
        top_k=int(os.environ.get("TOP_K", "3")),
        min_score=float(os.environ.get("MIN_SCORE", "0.4")),
    )
