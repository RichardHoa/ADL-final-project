SYSTEM_PROMPT = (
    "You are a helpful assistant for questions about the documents in the knowledge base. "
    "Answer only from the provided context. "
    "If the answer is not in the context, say that you don't know."
)


def build_prompt(question, chunks):
    context = "\n\n".join(f"[{chunk['source']}, page {chunk['page']}]\n{chunk['text']}" for chunk in chunks)
    return f"Context:\n{context}\n\nQuestion: {question}\nAnswer:"


def answer(question, knowledge_base, ollama, top_k):
    chunks = knowledge_base.search(question, top_k)
    text = ollama.generate(SYSTEM_PROMPT, build_prompt(question, chunks))
    citations = [{"document": chunk["source"], "page": chunk["page"], "snippet": chunk["text"]} for chunk in chunks]
    return text.strip(), citations
