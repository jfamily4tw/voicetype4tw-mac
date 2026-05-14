from .base import BaseLLM

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
    elif engine == "gemini":
        from .gemini import GeminiLLM
        return GeminiLLM(config)
    elif engine == "qwen":
        from .qwen import QwenLLM
        return QwenLLM(config)
    elif engine == "deepseek":
        from .deepseek import DeepSeekLLM
        return DeepSeekLLM(config)
    else:
        from .ollama import OllamaLLM
        return OllamaLLM(
            model=config.get("ollama_model", "llama3"),
            base_url=config.get("ollama_base_url", "http://localhost:11434"),
        )
