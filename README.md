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
CS Major Handbook_2026-2027.pdf: embedding 0/88
CS Major Handbook_2026-2027.pdf: embedding 16/88
...
CS Major Handbook_2026-2027.pdf: embedding 88/88
CS Major Handbook_2026-2027.pdf: storing
CS Major Handbook_2026-2027.pdf: 88 chunks
Ingested 1 document(s).
```

You can also pass a single file, e.g. `python -m rag.ingestion "/data/CS Major Handbook_2026-2027.pdf"`. Re-ingesting a file with the same name replaces its old Chunks.

### 3. Open the UI

Open http://localhost:5000.

- **Ask** a question in the box at the bottom, e.g. *"How many credits are required to graduate?"*. Press Enter to send, or Shift+Enter for a new line. A *Thinking…* indicator shows while the model works; on a CPU an answer can take tens of seconds.
- **Citations** appear under each answer as *Document, page N*. Click one to expand the snippet the model was given. **View prompt** opens that answer's Generation on the Logging page.
- **Conversations** are listed in the sidebar, most recently active first, and titled from their first question. Click one to reopen it, use **New chat** to start fresh, or **Delete** to remove one. History lives in SQLite, so it survives page reloads and container restarts.
- **Documents** shows everything in the knowledge base with its Chunk count. **Upload PDF or TXT** ingests a new file in the background. A progress bar shows each stage (reading pages, chunking, embedding *n/total* Chunks, storing), and the list refreshes when it's done. You can start several uploads at once, and reloading the page picks up any that are still running. Other file types are rejected with an error.

The nav bar links to two inspection pages:

- **RAG** (http://localhost:5000/rag) lists every Chunk in the knowledge base, 50 per page, filterable by Document and text. **Similarity search** runs a query exactly as chat retrieval does and returns every Chunk whose Similarity score (1 − cosine distance, from 0 to 1) is at or above the threshold you set, best first, up to *Max results*. The threshold only affects this page, not chat.
- **Logging** (http://localhost:5000/logging) has two tabs. **Generations** lists every Generation newest first: the retrieved Chunks with their scores, the exact system and user prompts sent to the model, the raw answer, the model, how long it took, and whether it failed. Failed Generations are logged with their error even though nothing is saved to the Conversation. Filter by Conversation, and click **Refresh** to load new entries. **chat.db** is a read-only browser for every table in the SQLite database.

## Everyday commands

All from `docker/`:

| Task | Command |
| --- | --- |
| Start (after the first build) | `docker compose up -d` |
| Rebuild after code changes | `docker compose up --build -d` |
| Run the tests | `docker compose run --rm app pytest` |
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
| `TOP_K` | `4` | Chunks retrieved per question |

Inside the container, `OLLAMA_HOST` (`http://ollama:11434`) and `STORAGE_DIR` (`/storage`) are fixed by `docker-compose.yml`. If you change `EMBED_MODEL`, reset storage and re-ingest, because embeddings from different models can't be compared.

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


