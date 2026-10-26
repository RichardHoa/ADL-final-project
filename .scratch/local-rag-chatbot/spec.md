# Local RAG handbook chatbot (Tasks 1–4)

Status: ready-for-agent

## Problem Statement

A student needs a chatbot for the CS311 final project that answers questions about the FUV B.S. Computer Science Major Handbook. It must run entirely on a local machine. The course's baseline RAG sample only reads `.txt` files, has no web interface, and has no reproducible deployment. The student has to show four things: PDF support (Task 1), a working handbook chatbot (Task 2), a Docker deployment (Task 3), and a browser UI with conversation history (Task 4). The target machine is an Ubuntu box that should need nothing but Docker.

## Solution

A self-contained local RAG application, started with a single `docker compose up`:

- An Ollama service hosts the embedding model (`nomic-embed-text`) and the language model (`qwen2.5:0.5b`). A one-shot init service pulls both models before the app starts.
- A Flask application ingests Documents (PDF and TXT) into a ChromaDB knowledge base, answers questions grounded in retrieved Chunks with Citations, and keeps every Conversation permanently in SQLite.
- A plain HTML/CSS/JS web UI (no frontend libraries) lets the user ask questions and read answers with their Citations. It also lets them browse, start and delete Conversations, upload a Document, and see which Documents are in the knowledge base.
- A CLI command ingests every Document in a folder. This is how the handbook gets indexed.

## User Stories

1. As a student, I want to start the whole system with one Docker Compose command, so that I don't need Python, Ollama or any other tool installed on the host.
2. As a student, I want the required Ollama models pulled automatically on first start, so that I don't have to run model downloads by hand.
3. As a student, I want the app to wait until the models are available before it starts, so that the first question doesn't fail because a model is missing.
4. As a student, I want to ingest every PDF in the dataset folder with one CLI command run inside the container, so that the handbook becomes searchable.
5. As a student, I want the CLI to print each Document it ingested and how many Chunks it produced, so that I can show in the Task 1 video that PDF processing worked.
6. As a student, I want the system to extract text from PDF files page by page, so that every Chunk records the page it came from.
7. As a student, I want TXT files supported as well, so that the baseline's original input format still works.
8. As a student, I want Documents split into overlapping Chunks of roughly 800 characters on paragraph and sentence boundaries, so that retrieved passages are coherent and fit in the prompt.
9. As a student, I want re-ingesting a Document with the same filename to replace its old Chunks, so that duplicates never crowd the retrieval results.
10. As a user, I want to upload a PDF or TXT file from the web UI, so that I can add a Document without touching the command line.
11. As a user, I want a clear error when I upload an unsupported file type, so that I know why nothing was ingested.
12. As a user, I want to see the list of ingested Documents with their Chunk counts, so that I can confirm an upload landed in the knowledge base.
13. As a user, I want to type a question and get an answer generated from the handbook, so that I can learn about program requirements, courses, learning outcomes and policies.
14. As a user, I want the chatbot to say it doesn't know when the retrieved context doesn't contain the answer, so that I'm not misled by invented facts.
15. As a user, I want each answer to show its Citations (Document name and page), so that I can check the answer against the handbook.
16. As a user, I want to expand a Citation to read the retrieved snippet, so that I can see exactly what text the model was given.
17. As a user, I want a "thinking…" indicator while the answer is being generated, so that I know the system is working on slow CPU inference.
18. As a user, I want every question and answer saved permanently, so that I never lose my chat history, even after restarting the containers.
19. As a user, I want a sidebar listing my Conversations newest first, each titled from its first question, so that I can find earlier chats.
20. As a user, I want to open a past Conversation and see all its Messages with their Citations, so that I can review earlier answers.
21. As a user, I want a "New chat" button, so that I can start a fresh Conversation.
22. As a user, I want to delete a Conversation, so that I can remove chats I no longer need.
23. As a user, I want each question answered independently of earlier turns, so that answers are predictable and easy to reproduce for the Task 2 analysis.
24. As a user, I want a readable, accessible interface that works on narrow screens and respects light/dark preference, so that the chatbot is comfortable to use in the demo.
25. As a user, I want a clear error message in the chat when the language model is unreachable or a request fails, so that I'm not left waiting forever.
26. As a student, I want the knowledge base, the SQLite database and uploaded files kept in a host folder that's mounted into the container, so that data survives container rebuilds and I can inspect it.
27. As a student, I want the dataset folder mounted read-only, so that the container can't modify the source handbook.
28. As a student, I want the test suite to run inside the container with one command, so that I can verify the build without a local Python setup.
29. As a student, I want the README to give step-by-step instructions for building, running, ingesting, using the UI, running tests, and resetting data, so that the grader can reproduce everything.
30. As a student, I want the repository laid out like the required submission folders, so that packaging the final zip is trivial.
31. As a student, I want a `.gitignore` that excludes runtime data, caches and video files, so that the repository only holds reproducible project assets.

## Implementation Decisions

- **Repository layout** mirrors the submission: a source-code folder (application, RAG modules, static frontend, tests, Python requirements), a docker folder (Dockerfile + compose file), and placeholder report and demo-video folders. The existing dataset folder stays at the root.
- **Code style**: written from scratch (the sample baseline isn't available), with minimal comments.
- **Modules**:
  - *Document loader*: given a file path, returns the Document's text as a list of (page number, text) pairs. Supports PDF (via pypdf, page by page) and TXT (a single page). Rejects other extensions.
  - *Chunker*: turns page texts into Chunks of about 800 characters with about 150 characters of overlap. It prefers paragraph, then sentence, then word boundaries, and each Chunk keeps its source filename and page.
  - *Ollama client*: a small wrapper exposing embed-texts and generate-answer, talking to the Ollama HTTP API at a configurable host. It's passed into the app at creation so tests can substitute a fake.
  - *Knowledge base*: a ChromaDB persistent collection. Operations: ingest a Document (delete existing Chunks with the same source, then add the new ones with embeddings), search the top-K Chunks for a question, and list Documents with Chunk counts. Embedding inputs use nomic's task prefixes (`search_document:` for Chunks, `search_query:` for questions).
  - *RAG answerer*: retrieves the top 4 Chunks for the question alone, builds the prompt (system instruction: answer only from the provided context; if it isn't there, say you don't know), calls the LLM once with no streaming, and returns the answer text plus Citations. No Conversation history goes into the prompt.
  - *Conversation store*: SQLite with two tables. `conversations` holds id, title (taken from the first question) and created/updated timestamps. `messages` holds id, conversation id, role (user/assistant), content, citations (JSON) and a created timestamp. Deleting a Conversation removes its Messages.
  - *Ingest CLI*: a Python module entry point that takes a folder (or file) path and ingests every supported Document in it, printing per-Document Chunk counts. It uses the same ingestion path as uploads.
  - *Flask app*: built by an app factory that takes configuration (storage directory, Ollama client). It serves the static frontend and a JSON API.
- **API contract** (JSON):
  - `GET /api/documents`: list of Documents with Chunk counts.
  - `POST /api/documents`: multipart file upload. Saves the file under storage/uploads, ingests it, returns the Document and its Chunk count. Unsupported type → 400.
  - `GET /api/conversations`: Conversations, newest first.
  - `POST /api/conversations`: creates an empty Conversation.
  - `GET /api/conversations/<id>`: the Conversation with its Messages.
  - `DELETE /api/conversations/<id>`: deletes it.
  - `POST /api/conversations/<id>/messages` with `{question}`: stores the user Message, answers it, stores the assistant Message with Citations, and returns the assistant Message. An empty question → 400. Ollama unreachable → 502 with an error message.
- **Frontend**: plain HTML, CSS and JS with no libraries. CSS follows the css-best-practices skill (cascade layers, design tokens on `:root`, dark mode, logical properties, visible focus, reduced motion). The layout has a sidebar (New chat, Conversation list with delete, Document list, upload button) and a chat pane (Messages, expandable Citations, question input, thinking indicator). Answers are rendered all at once, with no streaming.
- **Deployment**: Docker Compose with three services.
  - `ollama`: the official image, CPU only, with models in a named volume.
  - `ollama-init`: one-shot; pulls `nomic-embed-text` and `qwen2.5:0.5b`, then exits.
  - `app`: a python:3.11-slim image running gunicorn on port 5000 with a 300s timeout. It starts after `ollama-init` completes successfully, bind-mounts the host storage folder, and mounts the dataset folder read-only at `/data`.
  - Configuration (Ollama host, model names, storage path, top-K) comes from environment variables with the defaults above.
- **Out of the running path**: there's no auto-ingest on startup. The handbook gets indexed with the CLI.

## Testing Decisions

- Tests check external behaviour only, through two seams. Coverage is deliberately minimal at this stage: happy paths only, with deeper testing planned later.
- **Seam 1: the Flask HTTP API**, via the Flask test client. The app is built with a temp storage directory and a fake Ollama client: deterministic hashed bag-of-words embeddings, and a canned answer that echoes the prompt context. Happy-path cases:
  - uploading a generated PDF lists the Document with a Chunk count above zero
  - asking a question returns an answer and Citations naming the Document and page
  - the Conversation and its Messages can then be listed and reloaded
- **Seam 2: the ingest CLI**. Running it on a temp folder holding a generated PDF, with the same fake client, makes the Document appear in the knowledge base's Document list.
- Test PDFs are generated inside the tests, so no binary fixtures are committed. Nothing touches real Ollama or Docker.
- The tests run inside the app container with pytest. There's no prior test code in the repo; these are the first tests.

## Out of Scope

- Streaming responses.
- Choosing a model in the UI (only `qwen2.5:0.5b`).
- GPU support.
- Auto-ingesting the handbook on startup.
- Using Conversation history in the LLM prompt.
- The Task 2 evaluation question set and evaluation script (to be done later by the student).
- OCR for text inside images.
- Renaming or searching Conversations; deleting Documents from the UI.
- The report (Task 5) and the demo videos (Task 6).
- Error-path and edge-case tests.

## Further Notes

- The target machine is Ubuntu. The development Mac has neither Docker nor Ollama, so end-to-end verification happens on the Ubuntu machine.
- The handbook is the CS Major Handbook 2026–2027 (23 pages, cleanly extractable text).
- Answers are not expected to be fully correct with a 0.5b model. Citations exist so the student can explain failures in the Task 2 analysis.
