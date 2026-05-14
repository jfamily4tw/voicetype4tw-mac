from openai import OpenAI
from .base import BaseLLM


class OpenAILLM(BaseLLM):
    def __init__(self, config: dict):
        self.api_key = config.get("openai_api_key", "")
        self.model = config.get("openai_model", "gpt-4o-mini")
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None

    def refine(self, text: str, prompt: str) -> str:
        if not self.client:
            return text
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"<Draft>\n{text}\n</Draft>"},
            ],
            max_tokens=1024,
        )
        result = response.choices[0].message.content.strip()
        print(f"[llm] OpenAI refined: {result}")
        return result
