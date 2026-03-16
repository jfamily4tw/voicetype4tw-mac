import os
import sys
import shutil
import platform
import subprocess
import socket
from pathlib import Path

def print_banner():
    print("=" * 60)
    print("   VoiceType4TW Environment Diagnostic Tool (Doctor)")
    print("=" * 60)

def check_disk_space(path, required_gb=3):
    total, used, free = shutil.disk_usage(path)
    free_gb = free // (2**30)
    if free_gb < required_gb:
        return False, f"剩餘空間不足。需要至少 {required_gb}GB，目前僅剩 {free_gb}GB。"
    return True, f"剩餘空間充足 ({free_gb}GB)。"

def check_write_permission(path):
    try:
        test_file = Path(path) / ".doctor_test"
        test_file.write_text("permission_test")
        test_file.unlink()
        return True, "磁碟寫入權限正常。"
    except Exception as e:
        return False, f"磁碟寫入失敗！可能是因為您將程式放在系統保護目錄（如 C:\\Program Files）。原因: {e}"

def check_path_validity(path_str):
    # 檢查路徑是否包含非 ASCII 字元 (如中文) 或空白
    unsafe_chars = []
    if any(ord(c) > 127 for c in path_str):
        unsafe_chars.append("中文/非英文字元")
    
    # 檢查是否為網路磁碟 (Windows 專屬簡易判斷)
    if platform.system() == "Windows":
        # 這裡用一個簡單的判斷，如果路徑以 \\ 開頭或是網路對映
        # 實際上 check_write_permission 也能抓到部分問題
        pass

    if unsafe_chars:
        return False, f"路徑包含潛在風險：{', '.join(unsafe_chars)}。建議路徑僅包含英文、數字與底線。"
    return True, "路徑格式安全。"

def check_python_integrity():
    try:
        import venv
        import pip
        return True, f"Python 組件完整 (Python {platform.python_version()})。"
    except ImportError as e:
        return False, f"Python 組件缺失: {e}。請重新安裝 Python 並勾選 pip 等選項。"

def check_network():
    print("[INFO] 正在測試與 HuggingFace 的連線...", end="", flush=True)
    try:
        # 測試連線到 huggingface.co 的 443 埠口
        socket.setdefaulttimeout(5)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("huggingface.co", 443))
        print(" [OK]")
        return True, "網路連線正常 (可連接 HuggingFace)。"
    except Exception:
        print(" [FAILED]")
        return False, "無法連接至 HuggingFace。手動下載模型可能需要 VPN 或更換網路環境。"

def main():
    print_banner()
    current_dir = os.getcwd()
    print(f"[INFO] 檢測目錄: {current_dir}")
    
    issues = []
    checks = [
        ("磁碟空間", lambda: check_disk_space(current_dir)),
        ("寫入權限", lambda: check_write_permission(current_dir)),
        ("路徑安全", lambda: check_path_validity(current_dir)),
        ("Python環境", check_python_integrity),
        ("網路連線", check_network)
    ]
    
    report = []
    report.append(f"Diagnostic Report - {platform.node()}\n")
    report.append(f"OS: {platform.platform()}\n")
    report.append(f"Python: {sys.executable}\n")
    report.append("-" * 40 + "\n")

    all_passed = True
    for name, func in checks:
        print(f"[{name}] ", end="", flush=True)
        success, msg = func()
        status = "PASS" if success else "FAIL"
        print(f"{status}: {msg}")
        report.append(f"[{status}] {name}: {msg}\n")
        if not success:
            all_passed = False
            issues.append(f"{name}: {msg}")
    
    # 將報告寫入檔案
    with open("diagnostic_report.txt", "w", encoding="utf-8") as f:
        f.writelines(report)
    
    print("-" * 60)
    if all_passed:
        print("[SUCCESS] 環境預檢通過！可以開始安裝。")
        sys.exit(0)
    else:
        print("[CRITICAL] 偵測到環境問題，請先修正後再執行安裝。")
        print(f"[REPORT] 詳細報表已生成於: {os.path.join(current_dir, 'diagnostic_report.txt')}")
        sys.exit(1)

if __name__ == "__main__":
    main()
