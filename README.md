# ADL-final-project

A local RAG chatbot that answers questions about the FUV B.S. Computer Science Major Handbook (2026–2027). Everything runs on your own machine in Docker:

- **Ollama** serves the embedding model (`nomic-embed-text`) and the language model (`qwen2.5:0.5b`) on the CPU.
- **Flask** turns PDF and TXT Documents into Chunks, stores them in a **ChromaDB** knowledge base, answers questions from the top 4 Chunks with Citations (Document + page), and keeps every Conversation in **SQLite**.
- A **browser UI** in plain HTML, CSS and JavaScript lets you chat, browse past Conversations, and upload Documents.

Terms such as Document, Chunk, Citation and Conversation are defined in [GLOSSARY.md](GLOSSARY.md).

## Prerequisites

[Docker](https://docs.docker.com/engine/install/) with the Compose plugin (`docker compose version` should print a version). You don't need Python, Ollama or anything else on the host.

The first start downloads the Ollama and Python images plus both models (`nomic-embed-text` is about 270 MB and `qwen2.5:0.5b` about 400 MB), so it needs an internet connection and a few minutes. Later starts reuse the downloaded models, but `ollama-init` still checks the registry, so keep the machine online.

## Quick start

Run every command from the `docker/` folder.

```bash
git clone https://github.com/RichardHoa/ADL-final-project.git
cd ADL-final-project/docker
```

### 1. Build and start the stack

```bash
docker compose up --build -d
```

This starts three services in order:

1. `ollama`, the model server. Models are kept in the `ollama-models` named volume, so they are only downloaded once.
2. `ollama-init` pulls `nomic-embed-text` and `qwen2.5:0.5b`, then exits. **On the first run this takes a few minutes**, depending on your connection.
3. `app`, the Flask app on gunicorn. It starts only after `ollama-init` has finished successfully.

Watch progress with `docker compose logs -f ollama-init app`. When `docker compose ps` lists `app` as running, the stack is ready.

### 2. Ingest the handbook

The `Dataset/` folder is mounted read-only at `/data` inside the container. Ingest every PDF in it with the CLI:

```bash
docker compose exec app python -m rag.ingestion /data
```

### 3. Open the UI

Open http://localhost:5000.

## Everyday commands

All from `docker/`:

| Task | Command |
| --- | --- |
| Start (after the first build) | `docker compose up -d` |
| Rebuild after code changes | `docker compose up --build -d` |
| Run the tests | `docker compose run --rm app pytest` |
| Evaluate retrieval on the handbook | `docker compose run --rm app python -m rag.evaluation` |
| Follow the app logs | `docker compose logs -f app` |
| Follow all logs | `docker compose logs -f` |
| Stop (keeps data and models) | `docker compose down` |
| Reset chats, knowledge base and uploads | `docker compose down && sudo rm -rf ../storage` |
| Also delete the downloaded models | `docker compose down -v` |

The tests use a fake Ollama client, so they need neither the models nor the network. The container writes `storage/` as root, which is why resetting it needs `sudo`.

## Configuration

Set these in your shell or in a `docker/.env` file before `docker compose up`:

| Variable | Default | Meaning |
| --- | --- | --- |
| `EMBED_MODEL` | `nomic-embed-text` | Ollama embedding model |
| `LLM_MODEL` | `qwen2.5:0.5b` | Ollama language model |
| `TOP_K` | `3` | Most Chunks sent to the model per question |
| `MIN_SCORE` | `0.4` | Chunks scoring below this are never sent to the model |

Inside the container, `OLLAMA_HOST` (`http://ollama:11434`) and `STORAGE_DIR` (`/storage`) are fixed by `docker-compose.yml`. If you change `EMBED_MODEL`, reset storage and re-ingest, because embeddings from different models can't be compared.

## Retrieval

Each question is scored against the knowledge base in two ways:

- **Dense**: Ollama embeds the question and ChromaDB finds the 20 nearest Chunks by cosine similarity.
- **Keyword**: BM25 over every Chunk's text finds the 20 best keyword matches. Course codes match however they are written (`CS201` = `CS 201`), and common words like *how* or *the* are ignored.

The two candidate lists are merged and each Chunk gets a Retrieval score of `0.6 × dense + 0.4 × keyword`, both on a 0 to 1 scale. The best `TOP_K` (3) Chunks scoring at least `MIN_SCORE` (0.4) go to the model; if fewer than 3 pass, the model gets only those, and if none pass it gets no context and should say it doesn't know.