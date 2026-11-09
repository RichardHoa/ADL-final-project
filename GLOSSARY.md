# Glossary

**Document**: A source file (PDF or TXT) whose text the chatbot can answer from, e.g. the CS Major Handbook.

**Chunk**: A short passage of a Document's text, tagged with the Document it came from and its page number, and prefixed with the headings it sits under. Chunks are the unit that retrieval returns.

**Ingestion**: Turning a Document into Chunks and adding them to the knowledge base so they can be retrieved.

**Knowledge base**: The set of all ingested Chunks that retrieval searches.

**Citation**: A reference shown with an answer, pointing to the Chunk (Document + page) the answer drew on.

**Conversation**: An ordered series of Messages between a user and the chatbot, kept permanently. Each question is answered on its own: the model never sees earlier Messages, so there are no follow-up questions.

**Message**: One turn in a Conversation: either a user's question or the chatbot's answer (with its Citations).

**Similarity score**: How close a Chunk is in meaning to a question, from 0 (unrelated) to 1 (identical in meaning): the cosine similarity of their embeddings. Also called the dense score.

**Keyword score**: How much of a question's wording a Chunk contains, from 0 to 1: its BM25 score, where 1 means it has every distinctive word of the question.

**Retrieval score**: How well a Chunk matches a question overall: 0.6 × Similarity score + 0.4 × Keyword score. Retrieval ranks Chunks by it.

**Minimum score**: The lowest Retrieval score a Chunk can have and still count as a match (0.4 by default). Chat never sends the model a Chunk below it; the RAG page lets you set your own.

**Generation**: One request to the language model to answer a question: the retrieved Chunks, the exact prompt sent, and the model's raw answer.

**Generation log**: The record of every Generation, kept as long as its Conversation, so a user can see exactly what the model was given and what it returned.
