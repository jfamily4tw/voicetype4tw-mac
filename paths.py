import os
import sys
from pathlib import Path

IS_WINDOWS = sys.platform == "win32"

# Windows: %APPDATA%/VoiceType4TW
HOME = Path.home()
APP_DATA_DIR = Path(os.environ.get("APPDATA", str(HOME / "AppData" / "Roaming"))) / "VoiceType4TW"

# v2.8.27_V39: Side-effects moved to initialize_paths()

# 📄 基於指標的同步系統 (Synchronized Path Redirection)
# 儲存同步目錄的指標檔案 (此檔案永遠留於本機 AppData)
SYNC_POINTER_PATH = APP_DATA_DIR / "sync_path.txt"

def get_sync_base_dir() -> Path:
    """獲取目前的數據基礎目錄，若有同步指標則重定向至雲端目錄"""
    if SYNC_POINTER_PATH.exists():
        try:
            # v2.8.27: Try UTF-8 first, then fallback to localized encoding for Windows robustness
            try:
                path_str = SYNC_POINTER_PATH.read_text(encoding="utf-8").strip()
            except UnicodeDecodeError:
                path_str = SYNC_POINTER_PATH.read_text(encoding="mbcs").strip() 
                
            if path_str:
                sync_path = Path(path_str)
                # Check if path is valid and not containing placeholder characters like '?'
                if sync_path.exists() and sync_path.is_dir() and "?" not in str(sync_path):
                    return sync_path
        except Exception as e:
            print(f"[paths] Sync pointer error: {e}")
    # 預設：本機 Documents 內的 VoiceType4TW_Sync
    default_sync = Path.home() / "Documents" / "VoiceType4TW_Sync"
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

APP_CONFIG_DIR = APP_DATA_DIR
VERSION_NAME = "V2.9.6 Windows (BUILD-2960-STABLE)"
BUILD_ID = "BUILD-2960-STABLE"
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
    try:
        base_dir = Path(__file__).parent
        
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
            if not dest_dir.exists(): return
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
        
        # v2.8.27_V73: Privacy Filter for Sync Path Log
        display_path = str(SYNC_BASE_DIR).replace(str(Path.home()), "~")
        print(f"[paths] Data initialized. SYNC_BASE_DIR: {display_path}")
    except Exception as e:
        print(f"[paths] CRITICAL: Data initialization failed: {e}")

# v2.8.27_V39: Refactored to avoid redundant initialization in subprocesses.
# ONLY call this from main.py if is_main_process is True.
def initialize_paths():
    try:
        APP_DATA_DIR.mkdir(parents=True, exist_ok=True)

        # Ensure critical logs exist
        (APP_DATA_DIR / "debug.log").touch(exist_ok=True)
        (APP_DATA_DIR / "keystrike.log").touch(exist_ok=True)

        # Ensure sync dir exists
        try:
            get_sync_base_dir().mkdir(parents=True, exist_ok=True)
        except:
            pass

        _initialize_data()
    except Exception as e:
        print(f"[paths] Skip initialization: {e}")

# Note: Removed the automatic top-level call to _initialize_data()
# _initialize_data() 
