# Glossary

**Document**: A source file (PDF or TXT) whose text the chatbot can answer from, e.g. the CS Major Handbook.

**Chunk**: A short passage of a Document's text, tagged with the Document it came from and its page number. Chunks are the unit that retrieval returns.

**Ingestion**: Turning a Document into Chunks and adding them to the knowledge base so they can be retrieved.

**Knowledge base**: The set of all ingested Chunks that retrieval searches.

**Citation**: A reference shown with an answer, pointing to the Chunk (Document + page) the answer drew on.

**Conversation**: An ordered series of Messages between a user and the chatbot, kept permanently.

**Message**: One turn in a Conversation: either a user's question or the chatbot's answer (with its Citations).

**Similarity score**: How closely a Chunk matches a question, from 0 (unrelated) to 1 (identical in meaning). Retrieval ranks Chunks by it.

**Similarity threshold**: A minimum Similarity score; only Chunks at or above it count as matches. Used when inspecting the knowledge base, not when answering in chat.

**Generation**: One request to the language model to answer a question: the retrieved Chunks, the exact prompt sent, and the model's raw answer.

**Generation log**: The record of every Generation, kept as long as its Conversation, so a user can see exactly what the model was given and what it returned.
