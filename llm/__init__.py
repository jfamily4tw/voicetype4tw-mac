from .base import BaseLLM
from .prompts import get_default_system_prompt

def get_llm(config: dict) -> BaseLLM:
    engine = config.get("llm_engine", "ollama")
    
    if engine == "openai":
        from .openai_llm import OpenAILLM
        return OpenAILLM(config)
    elif engine == "claude":
        from .claude import ClaudeLLM
        return ClaudeLLM(config)
    elif engine == "openrouter":
        from .openrouter import OpenRouterLLM
        return OpenRouterLLM(config)
    elif engine == "apple_local":
        from .apple_local import AppleLocalLLM
        return AppleLocalLLM(config)
    elif engine == "gemini":
        from .gemini import GeminiLLM
        return GeminiLLM(config)
    elif engine == "qwen":
        from .qwen import QwenLLM
        return QwenLLM(config)
    elif engine == "deepseek":
        from .deepseek import DeepSeekLLM
        return DeepSeekLLM(config)
    elif engine == "minimax":
        from .minimax import MiniMaxLLM
        return MiniMaxLLM(config)
    else:
        from .ollama import OllamaLLM
        return OllamaLLM(config)
