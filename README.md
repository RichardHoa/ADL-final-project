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

The CLI prints each Ingestion stage as it goes (Chunks are embedded in batches of 16), then how many Chunks each Document produced:

```
CS Major Handbook_2026-2027.pdf: reading pages
CS Major Handbook_2026-2027.pdf: chunking
CS Major Handbook_2026-2027.pdf: embedding 0/99
CS Major Handbook_2026-2027.pdf: embedding 16/99
...
CS Major Handbook_2026-2027.pdf: embedding 99/99
CS Major Handbook_2026-2027.pdf: storing
CS Major Handbook_2026-2027.pdf: 99 chunks
Ingested 1 document(s).
```

You can also pass a single file, e.g. `python -m rag.ingestion "/data/CS Major Handbook_2026-2027.pdf"`. Re-ingesting a file with the same name replaces its old Chunks.

Chunking splits text at headings and prefixes each Chunk with the headings it sits under, e.g. `5. Concentrations in the Computer Science Major > 5.2 Available Concentrations > 5.2.2 Artificial Intelligence`, so a list of course codes still says which concentration it belongs to. Numbered section headings (`5.`, `5.2`, `5.2.2`), course headings (`CS302: ...`) and `APPENDIX` headings are recognised. After changing chunking, reset storage and re-ingest.

### 3. Open the UI

Open http://localhost:5000.

- **Ask** a question in the box at the bottom, e.g. *"How many credits are required to graduate?"*. Press Enter to send, or Shift+Enter for a new line. Each question is answered on its own: the model never sees earlier questions in the Conversation, so follow-ups like *"what about its prerequisites?"* won't work. Ask complete questions instead. A *Thinking…* indicator shows while the model works; on a CPU an answer can take tens of seconds.
- **Citations** appear under each answer as *Document, page N*. Click one to expand the snippet the model was given. **View prompt** opens that answer's Generation on the Logging page.
- **Conversations** are listed in the sidebar, most recently active first, and titled from their first question. Click one to reopen it, use **New chat** to start fresh, or **Delete** to remove one. History lives in SQLite, so it survives page reloads and container restarts.
- **Documents** shows everything in the knowledge base with its Chunk count. **Upload PDF or TXT** ingests a new file in the background. A progress bar shows each stage (reading pages, chunking, embedding *n/total* Chunks, storing), and the list refreshes when it's done. You can start several uploads at once, and reloading the page picks up any that are still running. Other file types are rejected with an error.

The nav bar links to two inspection pages:

- **RAG** (http://localhost:5000/rag) lists every Chunk in the knowledge base, 50 per page, filterable by Document and text. **Hybrid search** runs a query exactly as chat retrieval does and returns every Chunk whose Retrieval score is at or above the minimum you set, best first, up to *Max results*. Each result shows its Retrieval score and the dense and keyword scores it was built from. The minimum here only affects this page; chat always uses `MIN_SCORE`.
- **Logging** (http://localhost:5000/logging) has two tabs. **Generations** lists every Generation newest first: the retrieved Chunks with their scores, the exact system and user prompts sent to the model, the raw answer, the model, how long it took, and whether it failed. Failed Generations are logged with their error even though nothing is saved to the Conversation. Filter by Conversation, and click **Refresh** to load new entries. **chat.db** is a read-only browser for every table in the SQLite database.

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

### Evaluating retrieval

`python -m rag.evaluation` asks the 10 questions in `source_code/rag/evaluation/questions.json`, each tagged with the handbook page(s) that answer it, and prints the rank at which each ranking (hybrid, dense only, keyword only) first finds an answer page, plus whether that page was actually sent to the model. The handbook must be ingested first. Run it after changing chunking, the score weights, `TOP_K` or `MIN_SCORE` to see whether retrieval got better or worse.

## Storage

Runtime data goes in `storage/` at the repo root, which is bind-mounted into the app and ignored by git:

```
storage/
├── chroma/    # knowledge base (ChromaDB)
├── chat.db    # Conversations, Messages and the Generation log (SQLite)
└── uploads/   # Documents uploaded from the UI
```

## Improvement checklist

- [x] Show progress during Ingestion (upload UI and CLI)
- [x] A separate page (`/rag`) that shows all the Chunks and runs a similarity search with a custom threshold
- [x] A page (`/logging`) showing every prompt sent to the model and its answer, plus a read-only view of `chat.db`
- [x] Hybrid retrieval (dense + BM25) that sends at most 3 Chunks, all scoring at least 0.4
- [x] A 10-question retrieval evaluation (`python -m rag.evaluation`)


