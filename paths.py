import os
from pathlib import Path

# Get user home directory and create standard app support directory
HOME = Path.home()
import platform
IS_WINDOWS = platform.system() == "Windows"

if IS_WINDOWS:
    # Windows: %APPDATA%/VoiceType4TW
    APP_DATA_DIR = Path(os.environ.get("APPDATA", str(HOME / "AppData" / "Roaming"))) / "VoiceType4TW"
else:
    # macOS: ~/Library/Application Support/VoiceType4TW
    APP_DATA_DIR = HOME / "Library" / "Application Support" / "VoiceType4TW"

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

# Pre-define APP_DATA_DIR logic only, do not perform IO at top level.
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
VERSION_NAME = "V2.8.27 Windows Stable (V92-DIAGNOSTIC-VENV)"
BUILD_ID = "BUILD-2026-03-16-V92"
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
        # Perform directory creation and migration here ONLY
        APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
        migrate_legacy_data()
        
        # Ensure critical logs exist
        (APP_DATA_DIR / "debug.log").touch(exist_ok=True)
        (APP_DATA_DIR / "keystrike.log").touch(exist_ok=True)
        
        # New base sync dir check
        try:
            get_sync_base_dir().mkdir(parents=True, exist_ok=True)
        except:
            pass
            
        _initialize_data()
    except Exception as e:
        print(f"[paths] Skip initialization: {e}")

# Note: Removed the automatic top-level call to _initialize_data()
# _initialize_data() 
