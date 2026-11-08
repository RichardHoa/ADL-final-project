# ADL-final-project

A local RAG chatbot that answers questions about the FUV CS Major Handbook. It uses Ollama (`nomic-embed-text` + `qwen2.5:0.5b`), ChromaDB, Flask and SQLite, all running in Docker.

## Requirements

Docker with the Compose plugin. Nothing else is needed on the host.

## Run

All commands run from the `docker/` folder.

```bash
cd docker
docker compose up --build -d                                   # first start pulls both models (a few minutes)
docker compose exec app python -m rag.ingestion /data          # ingest the handbook (prints Chunks per Document)
```

Open http://localhost:5000 and ask a question.

| Task | Command |
| --- | --- |
| Run tests | `docker compose run --rm app pytest` |
| View logs | `docker compose logs -f app` |
| Stop | `docker compose down` |
| Reset data | `docker compose down && sudo rm -rf ../storage` (the container writes these files as root) |

Configuration is set with env vars: `OLLAMA_HOST`, `EMBED_MODEL`, `LLM_MODEL`, `STORAGE_DIR`, `TOP_K` (default `4`).
