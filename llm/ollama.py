import requests
from .base import BaseLLM


class OllamaLLM(BaseLLM):
    def __init__(self, model: str = "llama3", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url.rstrip("/")

    def refine(self, text: str, prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"<Draft>\n{text}\n</Draft>"},
            ],
            "stream": False,
        }
        try:
            # Use smaller timeout for local Ollama to fail fast if not running
            print(f"[llm] Ollama request -> {self.base_url}/api/chat model={self.model}")
            resp = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=5)
            resp.raise_for_status()
            result = resp.json()["message"]["content"].strip()
            print(f"[llm] Ollama refined: {result}")
            return result
        except Exception as e:
            print(f"[llm] Ollama error: {e}")
            # Fallback to original text to prevent thread crash
            return text
