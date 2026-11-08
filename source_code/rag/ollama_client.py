import requests


class OllamaError(RuntimeError):
    pass


class OllamaClient:
    def __init__(self, host, embed_model, llm_model, timeout=300):
        self._host = host.rstrip("/")
        self._embed_model = embed_model
        self._llm_model = llm_model
        self._timeout = timeout

    def embed(self, texts):
        return self._post("/api/embed", {"model": self._embed_model, "input": list(texts)})["embeddings"]

    def generate(self, system, prompt):
        payload = {
            "model": self._llm_model,
            "stream": False,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        }
        return self._post("/api/chat", payload)["message"]["content"]

    def _post(self, path, payload):
        try:
            response = requests.post(self._host + path, json=payload, timeout=self._timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as error:
            raise OllamaError(f"Could not reach Ollama at {self._host}: {error}") from error
