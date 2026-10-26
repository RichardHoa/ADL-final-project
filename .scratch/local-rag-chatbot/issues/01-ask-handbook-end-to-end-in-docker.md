# 01: Ask the handbook end-to-end in Docker

**What to build:** A student runs `docker compose up` on a host with only Docker installed. The Ollama service starts, the init service pulls `nomic-embed-text` and `qwen2.5:0.5b`, and then the Flask app starts. Running the ingest CLI inside the app container on the read-only dataset mount ingests the CS Handbook into the knowledge base and prints each Document with its Chunk count. A bare-bones page lets the user ask a question and see the answer with its Citations (Document + page). The full backend from the spec (`.scratch/local-rag-chatbot/spec.md`) is in place: Document upload and Document list, plus the Conversation and Message API persisted in SQLite. Each question is answered from the top 4 Chunks of the question alone, with no history in the prompt.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Docker Compose defines `ollama` (CPU, models in a named volume), a one-shot `ollama-init` that pulls both models, and `app` (python:3.11-slim, gunicorn on port 5000, 300s timeout). `app` starts only after `ollama-init` completes successfully.
- [ ] The storage folder (knowledge base, SQLite, uploads) is bind-mounted from the host; the dataset folder is mounted read-only at `/data`.
- [ ] Configuration (Ollama host, model names, storage path, top-K) comes from env vars with the spec defaults.
- [ ] PDF text is extracted page by page; TXT is supported; other types are rejected.
- [ ] Chunks are about 800 characters with about 150 overlap, split on paragraph/sentence boundaries, and each carries its source and page.
- [ ] Embeddings use nomic's `search_document:` / `search_query:` prefixes.
- [ ] Re-ingesting a Document with the same filename replaces its Chunks instead of duplicating them.
- [ ] The ingest CLI takes a folder or file path and prints per-Document Chunk counts.
- [ ] The JSON API matches the spec contract: Document list and upload, plus Conversation create, list, get and delete, and post a Message. Answers include Citations with Document, page and snippet.
- [ ] The prompt instructs the model to answer only from the context and to say it doesn't know otherwise.
- [ ] Conversations and Messages persist in SQLite. A Conversation is titled from its first question, and deleting it removes its Messages.
- [ ] A bare-bones page can ask a question and show the answer with Citations.
- [ ] The Ollama client is passed into the app factory. Happy-path pytest tests use a fake client:
  - API: upload a generated PDF → it's listed with Chunks > 0; ask → the answer has Citations; the Conversation reloads with its Messages
  - CLI: ingesting a temp folder makes the Document appear in the list
- [ ] The tests pass inside the app container via `docker compose run --rm app pytest`.
- [ ] Code is written from scratch with minimal comments.
