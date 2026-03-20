"""
記憶系統 - 跨 session 保存對話記憶，每週自動壓縮歸檔。

記憶存放路徑：~/voicetype_data/memory.json
歸檔路徑：~/voicetype_data/memory_archive/memory_YYYY-WNN.json
"""
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from paths import get_data_dir

DATA_DIR = get_data_dir("memory")
MEMORY_PATH = DATA_DIR / "memory.json"
ARCHIVE_DIR = DATA_DIR / "archive"

MAX_RECENT = 50        # memory.json 最多保留幾筆完整記錄
SUMMARY_KEEP = 5       # 帶給 LLM 的最近幾筆
ARCHIVE_DAYS = 7       # 超過幾天就歸檔


def _ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)


def load_memory() -> dict:
    """載入記憶檔，回傳 {entries: [...], summary: str, last_archive: str}"""
    _ensure_dirs()
    if MEMORY_PATH.exists():
        try:
            with open(MEMORY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"entries": [], "summary": "", "last_archive": ""}


def save_memory(memory: dict):
    _ensure_dirs()
    with open(MEMORY_PATH, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)


def add_entry(stt_text: str, llm_text: str):
    """新增一筆記憶（錄音結束後呼叫）"""
    memory = load_memory()
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "stt": stt_text,
        "llm": llm_text or stt_text,
    }
    memory["entries"].append(entry)
    # 超過上限時截掉最舊的
    if len(memory["entries"]) > MAX_RECENT:
        memory["entries"] = memory["entries"][-MAX_RECENT:]
    save_memory(memory)
    # 檢查是否需要歸檔
    maybe_archive(memory)


def get_context_for_llm(memory: Optional[dict] = None) -> str:
    """
    回傳給 LLM 的記憶上下文字串。
    包含：長期摘要（若有）+ 最近 SUMMARY_KEEP 筆對話。
    """
    if memory is None:
        memory = load_memory()
    parts = []
    if memory.get("summary"):
        parts.append(f"[長期記憶摘要]\n{memory['summary']}")
    recent = memory.get("entries", [])[-SUMMARY_KEEP:]
    if recent:
        lines = []
        for e in recent:
            ts = e.get("ts", "")[:16]
            text = e.get("llm") or e.get("stt", "")
            lines.append(f"- [{ts}] {text}")
        parts.append("[最近對話記錄]\n" + "\n".join(lines))
    return "\n\n".join(parts)


def maybe_archive(memory: Optional[dict] = None):
    """
    若距上次歸檔已超過 ARCHIVE_DAYS 天，
    將舊資料壓縮摘要後另存，memory.json 只保留摘要 + 最新幾筆。
    摘要由簡單文字拼接完成（不需要 LLM，避免循環依賴）。
    """
    if memory is None:
        memory = load_memory()
    last = memory.get("last_archive", "")
    if last:
        try:
            last_dt = datetime.fromisoformat(last)
            if (datetime.now() - last_dt).days < ARCHIVE_DAYS:
                return
        except Exception:
            pass

    entries = memory.get("entries", [])
    if len(entries) < 10:
        return  # 資料太少，不歸檔

    # 歸檔舊資料
    week_str = datetime.now().strftime("%Y-W%W")
    archive_path = ARCHIVE_DIR / f"memory_{week_str}.json"
    archive_data = {
        "archived_at": datetime.now().isoformat(timespec="seconds"),
        "entries": entries,
        "summary": memory.get("summary", ""),
    }
    with open(archive_path, "w", encoding="utf-8") as f:
        json.dump(archive_data, f, ensure_ascii=False, indent=2)

    # 產生緊湊摘要（用 digest 邏輯取代粗暴截斷）
    new_summary = _generate_digest(entries, memory.get("summary", ""))

    # memory.json 只保留最新 5 筆 + 新摘要
    memory["entries"] = entries[-5:]
    memory["summary"] = new_summary
    memory["last_archive"] = datetime.now().isoformat(timespec="seconds")
    save_memory(memory)
    print(f"[memory] 已歸檔至 {archive_path}")


def clear_memory():
    """清空所有記憶（保留歸檔）"""
    save_memory({"entries": [], "summary": "", "last_archive": ""})


def _generate_digest(entries: list, old_summary: str = "") -> str:
    """
    從一組 entries 產生緊湊的文字摘要，無需 LLM。
    包含：時間範圍、筆數、最常用詞彙、代表性短句。
    """
    import re
    from collections import Counter

    all_texts = [e.get("llm") or e.get("stt", "") for e in entries]
    full_text = " ".join(all_texts)

    # 最常用 2-6 字中文詞彙 (top 15)
    words = re.findall(r'[\u4e00-\u9fff]{2,6}', full_text)
    top_words = [w for w, _ in Counter(words).most_common(15)]

    # 代表性短句：5~35 字，最多 5 句
    sentences = []
    for text in all_texts:
        for part in re.split(r'[。！？；\n]', text):
            part = part.strip()
            if 5 <= len(part) <= 35:
                sentences.append(part)
    representative = list(dict.fromkeys(sentences))
    representative = sorted(representative, key=len)[:5]

    date_start = entries[0].get("ts", "")[:10] if entries else ""
    date_end   = entries[-1].get("ts", "")[:10] if entries else ""
    total_chars = sum(len(t) for t in all_texts)

    parts = [
        f"[{date_start}～{date_end} · {len(entries)} 筆 · {total_chars} 字]",
        f"主要用詞：{'、'.join(top_words) if top_words else '(無)'}",
    ]
    if representative:
        parts.append("代表語句：" + "；".join(representative))

    new_digest = "\n".join(parts)
    if old_summary:
        return old_summary + "\n\n" + new_digest
    return new_digest


def purge_and_summarize() -> int:
    """
    手動觸發：將目前所有記憶條目壓縮為緊湊摘要，清除原始記錄，
    並將原始資料歸檔至 archive/ 目錄保留備份。
    回傳被壓縮的筆數（0 表示無資料可壓縮）。
    """
    _ensure_dirs()
    memory = load_memory()
    entries = memory.get("entries", [])
    if not entries:
        return 0

    # 歸檔原始資料
    week_str = datetime.now().strftime("%Y-W%W")
    archive_path = ARCHIVE_DIR / f"memory_{week_str}_purge.json"
    with open(archive_path, "w", encoding="utf-8") as f:
        json.dump({
            "archived_at": datetime.now().isoformat(timespec="seconds"),
            "entries": entries,
            "previous_summary": memory.get("summary", ""),
        }, f, ensure_ascii=False, indent=2)

    new_summary = _generate_digest(entries, memory.get("summary", ""))
    count = len(entries)

    memory["entries"] = []
    memory["summary"] = new_summary
    memory["last_archive"] = datetime.now().isoformat(timespec="seconds")
    save_memory(memory)
    print(f"[memory] Purged {count} entries → digest saved. Archive: {archive_path}")
    return count
