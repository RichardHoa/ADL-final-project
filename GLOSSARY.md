# Glossary

**Document**: A source file (PDF or TXT) whose text the chatbot can answer from, e.g. the CS Major Handbook.

**Chunk**: A short passage of a Document's text, tagged with the Document it came from and its page number. Chunks are the unit that retrieval returns.

**Ingestion**: Turning a Document into Chunks and adding them to the knowledge base so they can be retrieved.

**Knowledge base**: The set of all ingested Chunks that retrieval searches.

**Citation**: A reference shown with an answer, pointing to the Chunk (Document + page) the answer drew on.

**Conversation**: An ordered series of Messages between a user and the chatbot, kept permanently.

**Message**: One turn in a Conversation: either a user's question or the chatbot's answer (with its Citations).
