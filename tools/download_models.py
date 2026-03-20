import os
import sys
import argparse
from pathlib import Path

# Fix for potential path issues
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def download_model_with_progress(model_size):
    try:
        from paths import APP_DATA_DIR
        from faster_whisper import WhisperModel
        
        cache_dir = APP_DATA_DIR / "whisper_models"
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\n[STT] Checking/Downloading model: {model_size}")
        print(f"[STT] Target directory: {cache_dir}")
        print("-" * 50)
        
        # faster-whisper will naturally use tqdm for progress
        # Since this is a CLI tool, standard tqdm output is fine
        model = WhisperModel(
            model_size, 
            device="cpu", # Force CPU for download to avoid DLL issues during setup
            compute_type="int8", 
            download_root=str(cache_dir)
        )
        
        print("-" * 50)
        print(f"[SUCCESS] Model '{model_size}' downloaded successfully.")
        return True
    except Exception as e:
        print(f"\n[ERROR] Failed to download model: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download Faster-Whisper models for VoiceType4TW")
    parser.add_argument("size", nargs="?", default="medium", help="Model size (tiny, base, small, medium, large-v3, etc.)")
    args = parser.parse_args()
    
    success = download_model_with_progress(args.size)
    sys.exit(0 if success else 1)
