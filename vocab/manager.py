"""
VocabManager - 管理自定義詞彙庫與自動記憶庫
- custom_vocab.json: 使用者手動新增的詞彙
- auto_memory.json: 自動從轉錄結果學習的常用詞彙
"""
import json
import os
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

from paths import get_data_dir

VOCAB_DIR = get_data_dir("vocab")
CUSTOM_VOCAB_PATH = VOCAB_DIR / "custom_vocab.json"
AUTO_MEMORY_PATH = VOCAB_DIR / "auto_memory.json"

AUTO_LEARN_THRESHOLD = 3
AUTO_MEMORY_MAX = 200

DEFAULT_VOCAB = [
    "Nebula", "OpenAI", "ChatGPT", "Claude", "Gemini", "Whisper",
    "OpenRouter", "GitHub", "Notion", "Slack", "Figma", "Vercel",
    "Python", "API", "UI", "UX", "SaaS", "SDK", "JSON", "CSV",
    "繁體中文", "人工智慧", "機器學習", "語音辨識", "自動化", "工作流程","OpenClaw",
]


def _ensure_dir():
    VOCAB_DIR.mkdir(parents=True, exist_ok=True)


def _init_default_vocab():
    _ensure_dir()
    with open(CUSTOM_VOCAB_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "_comment": "在 words 陣列中新增您常用的詞彙，例如人名、品牌名、專有名詞。這些詞彙會提示 Whisper 正確辨識。",
            "words": list(DEFAULT_VOCAB),
            "updated_at": datetime.now().isoformat(),
        }, f, ensure_ascii=False, indent=2)


def load_custom_vocab() -> list:
    _ensure_dir()
    if not CUSTOM_VOCAB_PATH.exists():
        _init_default_vocab()
        return list(DEFAULT_VOCAB)
    with open(CUSTOM_VOCAB_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("words", [])


def _save_custom_vocab(words: list):
    _ensure_dir()
    with open(CUSTOM_VOCAB_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "_comment": "在 words 陣列中新增您常用的詞彙，例如人名、品牌名、專有名詞。這些詞彙會提示 Whisper 正確辨識。",
            "words": words,
            "updated_at": datetime.now().isoformat(),
        }, f, ensure_ascii=False, indent=2)


def add_custom_word(word: str):
    word = word.strip()
    if not word:
        return
    words = load_custom_vocab()
    if word not in words:
        words.append(word)
        _save_custom_vocab(words)


def remove_custom_word(word: str):
    words = load_custom_vocab()
    words = [w for w in words if w != word]
    _save_custom_vocab(words)


def load_auto_memory() -> dict:
    _ensure_dir()
    if not AUTO_MEMORY_PATH.exists():
        return {}
    with open(AUTO_MEMORY_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("memory", {})


def _save_auto_memory(memory: dict):
    _ensure_dir()
    with open(AUTO_MEMORY_PATH, "w", encoding="utf-8") as f:
        json.dump({"memory": memory, "updated_at": datetime.now().isoformat()}, f, ensure_ascii=False, indent=2)


def learn_from_text(text: str):
    if not text:
        return
    memory = load_auto_memory()
    # 抓取 2-6 字的中文詞彙
    words = re.findall(r'[\u4e00-\u9fff]{2,6}', text)
    for word in words:
        memory[word] = memory.get(word, 0) + 1
    
    # 基礎清理：移除只出現一次且長度過短的（可選，目前保留以供手動升格）
    if len(memory) > AUTO_MEMORY_MAX:
        # 依次數排序，保留最多的
        memory = dict(Counter(memory).most_common(AUTO_MEMORY_MAX))
    _save_auto_memory(memory)


def learn_from_text_with_llm(llm_client, text: str):
    """使用 LLM 輔助提取專有名詞或關鍵字。"""
    if not llm_client or not text or len(text) < 5:
        return
    
    prompt = "你是語音辨識助手。請從以下文字中提取出 1-3 個可能的專有名詞、人名或專業術語（繁體中文）。只需回傳詞彙，以逗號分隔。如果沒有明顯的關鍵字，請回傳空字串。\n\n文字內容：\n"
    try:
        # 使用快速模式或特定的細簡 prompt
        keywords_str = llm_client.refine(text, prompt)
        if keywords_str:
            # 簡單清理
            keywords = [k.strip() for k in keywords_str.replace("，", ",").split(",") if k.strip()]
            if keywords:
                memory = load_auto_memory()
                for k in keywords:
                    # AI 抓到的詞給予較高的初始權重（例如 2 次）
                    memory[k] = memory.get(k, 0) + 2
                _save_auto_memory(memory)
                print(f"[vocab] AI 抓取到關鍵字: {keywords}")
    except Exception as e:
        print(f"[vocab] LLM 關鍵字提取失敗: {e}")


def load_all_learned_words() -> list:
    """回傳所有學到的詞彙，包含未達門檻的。"""
    memory = load_auto_memory()
    # 依出現次數排序
    return [w for w, c in sorted(memory.items(), key=lambda x: -x[1])]


def promote_learned_word(word: str):
    """將學到的詞彙變為自訂詞彙（永久保存）。"""
    word = word.strip()
    if not word: return
    
    # 1. 加入自訂
    add_custom_word(word)
    
    # 2. 從自動學習清單移除，避免重複顯示
    memory = load_auto_memory()
    if word in memory:
        del memory[word]
        _save_auto_memory(memory)


def get_frequent_words(threshold: int = AUTO_LEARN_THRESHOLD) -> list:
    memory = load_auto_memory()
    return [w for w, c in sorted(memory.items(), key=lambda x: -x[1]) if c >= threshold]


def build_vocab_prompt() -> str:
    custom = load_custom_vocab()
    frequent = get_frequent_words()
    all_words = list(dict.fromkeys(custom + frequent))
    if not all_words:
        return "以下是繁體中文的語音內容："
    words_str = "、".join(all_words[:50])
    return f"以下是繁體中文的語音內容，常用詞彙包含：{words_str}。"


def _edit_distance_1(a: str, b: str) -> bool:
    """快速判斷兩字串 edit distance 是否 <= 1（支援替換、插入、刪除）。"""
    if a == b:
        return True
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return False
    if la == lb:
        diff = sum(1 for x, y in zip(a, b) if x != y)
        return diff == 1
    # 長度差 1：檢查插入/刪除
    shorter, longer = (a, b) if la < lb else (b, a)
    i = j = diff = 0
    while i < len(shorter) and j < len(longer):
        if shorter[i] != longer[j]:
            diff += 1
            if diff > 1:
                return False
            j += 1
        else:
            i += 1
            j += 1
    return True


def apply_vocab_correction(text: str) -> str:
    """
    STT 後修正同音異字錯誤：對自訂詞彙中 >=3 字的詞，
    在輸出文字中掃描 edit-distance <= 1 的相似子串，強制替換為正確版本。
    例：私人詞庫有「嘴炮輸入法」，STT 輸出「嘴砲輸入法」→ 自動修正。
    """
    if not text:
        return text
    custom = load_custom_vocab()
    # 只處理 3 字以上的詞，避免過度替換短詞
    targets = sorted([w for w in custom if len(w) >= 3], key=len, reverse=True)
    for vocab_word in targets:
        wlen = len(vocab_word)
        i = 0
        result = []
        while i <= len(text) - wlen:
            substr = text[i:i + wlen]
            if substr == vocab_word:
                result.append(vocab_word)
                i += wlen
            elif _edit_distance_1(substr, vocab_word):
                result.append(vocab_word)
                i += wlen
                print(f"[vocab] 修正: 「{substr}」→「{vocab_word}」")
            else:
                result.append(text[i])
                i += 1
        result.append(text[i:])
        text = "".join(result)
    return text


def remove_learned_word(word: str):
    """從 AI 學習清單直接刪除，不升格為自訂詞彙。"""
    memory = load_auto_memory()
    if word in memory:
        del memory[word]
        _save_auto_memory(memory)
