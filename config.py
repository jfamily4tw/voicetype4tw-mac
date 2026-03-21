import json
import os

DEFAULT_CONFIG = {
    "hotkey_ptt": "alt_r",
    "hotkey_toggle": "f13",
    "hotkey_llm": "f14",
    # STT
    "stt_engine": "mlx_whisper",
    "whisper_model": "medium",
    "groq_api_key": "",
    "language": "zh",
    # LLM
    "llm_enabled": False,
    "llm_engine": "ollama",
    "llm_mode": "replace",   # "replace" | "fast"
    "llm_prompt": "",        # 留空使用內建 prompt
    "ollama_model": "llama3",
    "ollama_base_url": "http://localhost:11434",
    "openai_api_key": "",
    "openai_model": "gpt-4o-mini",
    "anthropic_api_key": "",
    "anthropic_model": "claude-3-haiku-20240307",
    "openrouter_api_key": "",
    "openrouter_model": "google/gemini-2.0-flash-001",
    "gemini_api_key": "",
    "gemini_model": "gemini-2.0-flash",
    "gemini_stt_model": "gemini-2.0-flash",
    "qwen_api_key": "",
    "qwen_model": "qwen-plus",
    "deepseek_api_key": "",
    "deepseek_model": "deepseek-chat",
    # 記憶
    "memory_enabled": True,
    # v2.5 靈魂系統
    "active_scenario": "default",
    "active_format": "natural",
    "action_mode": False,
    # 統計 / Debug
    "debug_mode": False,
    "is_demo": False,
    # 其他
    "auto_paste": True,
    "magic_trigger": "嘿 VoiceType",
    # UI
    "ui_skin": "titanium",
    # 麥克風
    "mic_device": None,   # None = 系統預設
    "mic_gain": 50,       # 視覺音量感度倍率 (5~200)
    "mic_gain_auto": True, # 自動調整感度
}
# 🗝️ 本地設定白名單 (不進行雲端同步的項目)
LOCAL_KEYS = {
    "hotkey_ptt", "hotkey_toggle", "hotkey_llm", "hotkey",
    "trigger_mode", "show_floating_button", "completion_sound",
    "debug_mode", "is_demo", "output_prefix",
    "separate_keystrike_log", "showcase_mode",
    "stt_engine", "whisper_model", "ui_skin",
    "mic_device", "mic_gain", "mic_gain_auto",
}

from paths import GLOBAL_CONFIG_PATH, LOCAL_CONFIG_PATH, APP_DATA_DIR

def load_config() -> dict:
    """載入設定：合併本機設定與全域同步設定。"""
    config = DEFAULT_CONFIG.copy()
    
    # 0. 舊版 config.json 遷移邏輯 (v2.9.0 升級防護)
    old_config_path = APP_DATA_DIR / "config.json"
    if old_config_path.exists():
        try:
            with open(old_config_path, "r", encoding="utf-8") as f:
                legacy_config = json.load(f)
            # 先跟目前的 config 合併（確保 legacy 有值的地方蓋掉 default）
            config.update(legacy_config)
            # 立即觸發拆分儲存，這樣會產生 config_local.json 與 config_global.json
            save_config(config) 
            # 成功遷移後刪除舊檔
            os.remove(old_config_path)  
        except Exception:
            pass

    # 1. 載入全域設定 (Global) - 優先權低
    if os.path.exists(GLOBAL_CONFIG_PATH):
        try:
            with open(GLOBAL_CONFIG_PATH, "r", encoding="utf-8") as f:
                global_data = json.load(f)
            # 過濾掉不該出現在全域的本地 key
            config.update({k: v for k, v in global_data.items() if k not in LOCAL_KEYS})
        except Exception:
            pass

    # 2. 載入本機設定 (Local) - 優先權高
    if os.path.exists(LOCAL_CONFIG_PATH):
        try:
            with open(LOCAL_CONFIG_PATH, "r", encoding="utf-8") as f:
                local_data = json.load(f)
            config.update(local_data)
        except Exception:
            pass

    return config


def save_config(config: dict) -> None:
    """儲存設定：依據白名單拆分並分別寫入本機與同步目錄。"""
    # 拆分資料
    local_data = {k: v for k, v in config.items() if k in LOCAL_KEYS}
    global_data = {k: v for k, v in config.items() if k not in LOCAL_KEYS}

    # 儲存本機配置
    try:
        with open(LOCAL_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(local_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[config] Error saving local config: {e}")

    # 儲存全域配置
    try:
        # 確保全域所在的父目錄存在 (可能在 NAS 上)
        GLOBAL_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(GLOBAL_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(global_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[config] Error saving global config: {e}")
