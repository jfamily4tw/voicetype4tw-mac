from .base import BaseSTT
from config import resolve_stt_engine

# Lazy imports: 各引擎只在選中時才 import，避免未安裝的套件造成啟動失敗。

def get_stt(config: dict) -> BaseSTT:
    engine = resolve_stt_engine(config.get("stt_engine"))
    if engine == "mlx_whisper":
        from .mlx_whisper import MLXWhisperSTT
        return MLXWhisperSTT(config)
    elif engine == "groq":
        from .groq_whisper import GroqWhisperSTT
        return GroqWhisperSTT(config)
    elif engine == "openrouter":
        from .openrouter_stt import OpenRouterSTT
        return OpenRouterSTT(config)
    elif engine == "gemini":
        from .gemini_stt import GeminiSTT
        return GeminiSTT(config)
    else:
        from .local_whisper import LocalWhisperSTT
        return LocalWhisperSTT(config)
