import os
from pathlib import Path

HOME = Path.home()

# macOS: ~/Library/Application Support/VoiceType4TW
APP_DATA_DIR = HOME / "Library" / "Application Support" / "VoiceType4TW"

# ── 版本分流：free | coffee ──────────────────────────────────────
# 打包不同版本時只需修改此一行
EDITION = "coffee"  # "free" | "coffee"

# v2.9.1: Legacy Migration Logic
def migrate_legacy_data():
    legacy_paths = [
        HOME / "Library" / "Application Support" / "嘴炮輸入法",
        HOME / "Library" / "Application Support" / "嘴砲輸入法"
    ]
    for lp in legacy_paths:
        if lp.exists() and lp.is_dir():
            print(f"[paths] Migrating legacy data from {lp} to {APP_DATA_DIR}")
            for item in lp.iterdir():
                target = APP_DATA_DIR / item.name
                try:
                    import shutil
                    if item.is_dir():
                        if not target.exists():
                            shutil.copytree(item, target)
                        else:
                            # Merge existing directories instead of skipping
                            for sub_item in item.iterdir():
                                sub_target = target / sub_item.name
                                if not sub_target.exists():
                                    if sub_item.is_dir():
                                        shutil.copytree(sub_item, sub_target)
                                    else:
                                        shutil.copy2(sub_item, sub_target)
                    else:
                        if not target.exists():
                            shutil.copy2(item, target)
                    print(f"[paths] Migrated {item.name}")
                except Exception as e:
                    print(f"[paths] Migration error for {item.name}: {e}")

# Ensure the directory exists and migrate
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
migrate_legacy_data()

# v2.8.12-dev: Force create critical log files to prevent UI error
(APP_DATA_DIR / "debug.log").touch(exist_ok=True)
(APP_DATA_DIR / "keystrike.log").touch(exist_ok=True)

# 📄 基於指標的同步系統 (Synchronized Path Redirection)
# 儲存同步目錄的指標檔案 (此檔案永遠留於本機 AppData)
SYNC_POINTER_PATH = APP_DATA_DIR / "sync_path.txt"

def get_sync_base_dir() -> Path:
    """獲取目前的數據基礎目錄，若有同步指標則重定向至雲端目錄"""
    if SYNC_POINTER_PATH.exists():
        try:
            path_str = SYNC_POINTER_PATH.read_text(encoding="utf-8").strip()
            if path_str:
                sync_path = Path(path_str)
                if sync_path.exists() and sync_path.is_dir():
                    return sync_path
        except Exception:
            pass
    # 預設：本機 Documents 內的 VoiceType4TW_Sync
    default_sync = Path("~/Documents/VoiceType4TW_Sync").expanduser()
    default_sync.mkdir(parents=True, exist_ok=True)
    return default_sync

# 核心同步目錄
SYNC_BASE_DIR = get_sync_base_dir()

# 設定檔拆分：本機 (Local) 與 全域同步 (Global)
# 本機設定 (永遠存放於 AppData，存放熱鍵等裝置特定資訊)
LOCAL_CONFIG_PATH = APP_DATA_DIR / "config_local.json"
# 全域設定 (可跟隨指標同步，存放 API Key 與 Prompt)
GLOBAL_CONFIG_PATH = SYNC_BASE_DIR / "config_global.json"

# v2.5 新版三層式靈魂目錄 (動態跟隨 SYNC_BASE_DIR)
SOUL_DIR = SYNC_BASE_DIR / "soul"
SOUL_SCENARIO_DIR = SOUL_DIR / "scenario"
SOUL_BASE_PATH = SOUL_SCENARIO_DIR / "default.md"
SOUL_FORMAT_DIR = SOUL_DIR / "format"
SOUL_TEMPLATE_DIR = SOUL_DIR / "templates"
SOUL_SNIPPET_DIR = SOUL_DIR / "snippets"

# 其他需同步的資料目錄
VOCAB_DIR = SYNC_BASE_DIR / "vocab"
MEMORY_DIR = SYNC_BASE_DIR / "memory"
STATS_DIR = SYNC_BASE_DIR / "stats"
AI_PERMANENT_MEMORY_PATH = SYNC_BASE_DIR / "ai_permanent_memory.md"

BUILD_ID = "BUILD-2970-DEV"
VERSION_NAME = f"2.9.7 {'Coffee' if EDITION == 'coffee' else 'Free'} Edition"
KEYSTRIKE_LOG_PATH = APP_DATA_DIR / "keystrike.log"

# 舊版路徑 (用於遷移)
OLD_SOUL_PATH = APP_DATA_DIR / "soul.md"

import shutil
import sys

def get_data_dir(subfolder: str) -> Path:
    d = APP_DATA_DIR / subfolder
    d.mkdir(parents=True, exist_ok=True)
    return d

# Initial data migration
def _initialize_data():
    res_path = os.environ.get("RESOURCEPATH")
    base_dir = Path(res_path) if res_path else Path(__file__).parent
    
    # 建立目錄
    SOUL_DIR.mkdir(parents=True, exist_ok=True)
    SOUL_SCENARIO_DIR.mkdir(parents=True, exist_ok=True)
    SOUL_FORMAT_DIR.mkdir(parents=True, exist_ok=True)
    SOUL_TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    SOUL_SNIPPET_DIR.mkdir(parents=True, exist_ok=True)

    # 1. 舊版單一 soul.md 遷移至 soul/base.md
    if OLD_SOUL_PATH.exists() and not SOUL_BASE_PATH.exists():
        try:
            shutil.move(str(OLD_SOUL_PATH), str(SOUL_BASE_PATH))
        except Exception:
            pass

    # 2. 複製內建模板 (情境與格式)
    def sync_defaults(sub_path, dest_dir):
        # v2.8.2-stable: 如果目標目錄已經有檔案，則不執行自動補回，尊重使用者的刪除與修改
        if any(dest_dir.iterdir()):
            return
            
        src_dir = base_dir / sub_path
        if src_dir.exists():
            for f in src_dir.glob("*.md"):
                dest_file = dest_dir / f.name
                if not dest_file.exists():
                    try:
                        shutil.copy2(f, dest_file)
                    except Exception:
                        pass

    sync_defaults("soul/scenario", SOUL_SCENARIO_DIR)
    sync_defaults("soul/format", SOUL_FORMAT_DIR)

    # Template copy logic removed (handled by config.py defaults)
    
    # 複製內建模板 (如果有在 bundle 裡的話)
    # 這裡暫時依賴 main.py 啟動時自動檢查
    print(f"[paths] Data initialized. SYNC_BASE_DIR is mapped to: {SYNC_BASE_DIR}")
    
_initialize_data()
