import anthropic
from .base import BaseLLM


class ClaudeLLM(BaseLLM):
    def __init__(self, config: dict):
        self.api_key = config.get("anthropic_api_key", "")
        self.model = config.get("anthropic_model", "claude-3-haiku-20240307")
        self.client = anthropic.Anthropic(api_key=self.api_key) if self.api_key else None

    def refine(self, text: str, prompt: str) -> str:
        if not self.client:
            return text
        message = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=prompt,
            messages=[{"role": "user", "content": f"<Draft>\n{text}\n</Draft>"}],
        )
        result = message.content[0].text.strip()
        print(f"[llm] Claude refined: {result}")
        return result
