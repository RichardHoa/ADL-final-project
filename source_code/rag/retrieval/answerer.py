import time

from rag.ollama_client import OllamaError

SYSTEM_PROMPT = (
    "You are a helpful assistant for questions about the documents in the knowledge base. "
    "Answer only from the provided context. "
    "If the answer is not in the context, say that you don't know."
)


def build_prompt(question, chunks):
    context = "\n\n".join(f"[{chunk['document']}, page {chunk['page']}]\n{chunk['text']}" for chunk in chunks)
    return f"Context:\n{context}\n\nQuestion: {question}\nAnswer:"


def answer(question, knowledge_base, ollama, top_k):
    """Run one Generation. Ollama failures are recorded in "error" rather than raised."""
    generation = {
        "question": question,
        "chunks": [],
        "system_prompt": SYSTEM_PROMPT,
        "user_prompt": None,
        "answer": None,
        "error": None,
    }
    started = time.monotonic()
    try:
        generation["chunks"] = knowledge_base.search(question, top_k)
        generation["user_prompt"] = build_prompt(question, generation["chunks"])
        generation["answer"] = ollama.generate(SYSTEM_PROMPT, generation["user_prompt"]).strip()
    except OllamaError as error:
        generation["error"] = str(error)
    generation["duration_ms"] = round((time.monotonic() - started) * 1000)
    return generation


def citations(generation):
    return [{"document": chunk["document"], "page": chunk["page"], "snippet": chunk["text"]} for chunk in generation["chunks"]]
