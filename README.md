# ADL-final-project

A local RAG chatbot that answers questions about the FUV B.S. Computer Science Major Handbook (2026–2027). Everything runs on your own machine in Docker:

- **Ollama** serves the embedding model (`nomic-embed-text`) and the language model (`qwen2.5:0.5b`) on the CPU.
- **Flask** turns PDF and TXT Documents into Chunks, stores them in a **ChromaDB** knowledge base, answers questions from the best-matching Chunks with Citations (Document + page), and keeps every Conversation in **SQLite**.
- A **browser UI** in plain HTML, CSS and JavaScript lets you chat, browse past Conversations, and upload Documents.

Terms such as Document, Chunk, Citation and Conversation are defined in [GLOSSARY.md](GLOSSARY.md).

## Installation instructions

Clone the repository and move into the `docker/` folder. Every command in this README runs from there.

```bash
git clone https://github.com/RichardHoa/ADL-final-project.git
cd ADL-final-project/docker
```

Then build and start the stack as described in [Docker deployment](#docker-deployment). There is nothing to install on the host besides Docker.

## Required dependencies

On the host you only need [Docker](https://docs.docker.com/engine/install/) with the Compose plugin (`docker compose version` should print a version). You don't need Python, Ollama or anything else.

Docker pulls or builds everything else:

| Component | Version | Where it comes from |
| --- | --- | --- |
| Ollama | `ollama/ollama:0.12.6` | Docker image |
| Python | 3.11 | `python:3.11-slim` base image |
| `nomic-embed-text` (about 270 MB) | latest | Pulled by `ollama-init` |
| `qwen2.5:0.5b` (about 400 MB) | latest | Pulled by `ollama-init` |
| Flask, gunicorn, pypdf, ChromaDB, requests, pytest, fpdf2 | pinned | [`source_code/requirements.txt`](source_code/requirements.txt), installed in the image |

The first start downloads the images and both models, so it needs an internet connection and a few minutes. Later starts reuse the downloaded models, but `ollama-init` still checks the registry, so keep the machine online.

## Docker deployment

### 1. Build and start the stack

```bash
docker compose up --build -d
```

This starts three services in order:

1. `ollama`, the model server. Models are kept in the `ollama-models` named volume, so they are only downloaded once.
2. `ollama-init` pulls `nomic-embed-text` and `qwen2.5:0.5b`, then exits. **On the first run this takes a few minutes**, depending on your connection.
3. `app`, the Flask app on gunicorn, published on port 5000. It starts only after `ollama-init` has finished successfully.

Watch progress with `docker compose logs -f ollama-init app`. When `docker compose ps` lists `app` as running, the stack is ready.

The `app` container mounts two folders from the repository:

- `Dataset/` at `/data`, read-only, holding the Documents to ingest.
- `storage/` at `/storage`, holding the knowledge base, Conversations and uploads, so they survive restarts.

### 2. Ingest the handbook

Ingest every PDF in `Dataset/` with the CLI:

```bash
docker compose exec app python -m rag.ingestion /data
```

### 3. Open the UI

Open http://localhost:5000.

### Everyday commands

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

### Configuration

Set these in your shell or in a `docker/.env` file before `docker compose up`:

| Variable | Default | Meaning |
| --- | --- | --- |
| `EMBED_MODEL` | `nomic-embed-text` | Ollama embedding model |
| `LLM_MODEL` | `qwen2.5:0.5b` | Ollama language model |
| `TOP_K` | `3` | Most Chunks sent to the model per question |
| `MIN_SCORE` | `0.4` | Chunks scoring below this are never sent to the model |

Inside the container, `OLLAMA_HOST` (`http://ollama:11434`) and `STORAGE_DIR` (`/storage`) are fixed by `docker-compose.yml`. If you change `EMBED_MODEL`, reset storage and re-ingest, because embeddings from different models can't be compared.

## Example usage

### Ask a question

With the handbook ingested, open http://localhost:5000, start a new Conversation and ask, for example:

- *How many credits are required for the Computer Science major requirements?*
- *What minimum major GPA do I need to enroll in Capstone I?*
- *What are the prerequisites for CS302 Algorithms & Theory of Computing?*

The answer comes back with Citations naming the Document and the pages it was drawn from. Past Conversations are listed in the sidebar and can be reopened.

### Add your own Documents

Upload a PDF or TXT file from the UI, or put it in `Dataset/` and ingest it from the CLI. The CLI takes a single file or a folder:

```bash
docker compose exec app python -m rag.ingestion "/data/CS Major Handbook_2026-2027.pdf"
```

### Measure retrieval

`docker compose run --rm app python -m rag.evaluation` asks the questions in [`source_code/rag/evaluation/questions.json`](source_code/rag/evaluation/questions.json) and reports how often retrieval finds the Chunk that answers each one. Pass another questions file as an argument to evaluate your own set.

### How a question is answered

Each question is scored against the knowledge base in two ways:

- **Dense**: Ollama embeds the question and ChromaDB finds the 20 nearest Chunks by cosine similarity.
- **Keyword**: BM25 over every Chunk's text finds the 20 best keyword matches. Course codes match however they are written (`CS201` = `CS 201`), and common words like *how* or *the* are ignored.

The two candidate lists are merged and each Chunk gets a Retrieval score of `0.6 × dense + 0.4 × keyword`, both on a 0 to 1 scale. The best `TOP_K` (3) Chunks scoring at least `MIN_SCORE` (0.4) go to the model; if fewer than 3 pass, the model gets only those, and if none pass it gets no context and should say it doesn't know.

## Known limitations

- **Small CPU model.** `qwen2.5:0.5b` keeps the stack light, but answers can be slow on modest hardware and the model sometimes misreads or ignores the retrieved Chunks. A larger `LLM_MODEL` answers better at the cost of speed and memory.
- **No follow-up memory.** Conversations are saved, but each question is answered on its own; earlier turns are not sent to the model, so questions like *"what about its prerequisites?"* lose their context.
- **PDF and TXT only, no OCR.** Text is extracted with pypdf, so scanned PDFs yield no Chunks and table layouts are flattened into plain text.
- **Online at every start.** `ollama-init` checks the model registry each time the stack starts, so it fails without an internet connection.
- **Single user, no authentication.** Anyone who can reach port 5000 can read every Conversation and upload Documents. Gunicorn runs one worker with four threads, so a handful of simultaneous questions queue behind each other.
- **Changing the embedding model needs a full re-ingest**, because embeddings from different models can't be compared.