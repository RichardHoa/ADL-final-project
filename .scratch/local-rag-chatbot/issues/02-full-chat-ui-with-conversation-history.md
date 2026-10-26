# 02: Full chat UI with Conversation history

**What to build:** The bare-bones page is replaced with the real browser chatbot, in plain HTML/CSS/JS with no frontend libraries. A user can do all of this without leaving the browser:
- see their saved Conversations newest first, open one to read all its Messages with Citations, start a New chat, and delete a Conversation
- see the ingested Documents with their Chunk counts, and upload a PDF or TXT that appears in that list
- ask questions, see a thinking indicator while the answer is generated, and expand Citations to read the retrieved snippets
- see a clear error in the chat when a request fails

The repo also gets the final README with detailed step-by-step instructions for running everything with Docker only. See `.scratch/local-rag-chatbot/spec.md`.

**Blocked by:** 01 (Ask the handbook end-to-end in Docker)

**Status:** ready-for-agent

- [ ] The sidebar shows Conversations newest first, titled from their first question, with New chat and delete. Clicking one loads its Messages and Citations.
- [ ] The sidebar shows the Document list with Chunk counts and an upload button. A successful upload refreshes the list, and an unsupported type shows an error.
- [ ] The chat pane shows user and assistant Messages, Citations (Document + page) expandable to their snippet, a thinking indicator while waiting, and inline error messages. Answers render all at once (no streaming).
- [ ] Chat history survives page reloads and container restarts, because it's read from the SQLite-backed API.
- [ ] The CSS follows the css-best-practices skill:
  - cascade layers and design tokens on `:root`
  - light/dark via `prefers-color-scheme`
  - logical properties
  - visible focus and reduced motion
  - a layout that works at phone width
- [ ] No frontend libraries or frameworks are used.
- [ ] The README covers:
  - prerequisites (Docker only)
  - building and starting the stack, and first-run model pull time
  - ingesting the handbook with the CLI
  - opening the UI and uploading a Document
  - running the tests in the container, viewing logs, stopping, and resetting storage
  - repo layout and known limitations
- [ ] `.gitignore` excludes runtime storage, Python caches, virtualenvs and video files.
- [ ] Placeholder report and demo-video folders exist.
