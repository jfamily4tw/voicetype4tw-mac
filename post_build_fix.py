import os
import shutil
import subprocess
from pathlib import Path

def get_site_packages_path():
    import site
    # 優先查詢目前 Python 的 site-packages
    candidates = list(site.getsitepackages())
    # 加入 python3.12 framework 路徑（打包時可能用不同的 python 執行此腳本）
    candidates += [
        "/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/site-packages",
        "/usr/local/lib/python3.12/site-packages",
    ]
    for p in candidates:
        if (Path(p) / "mlx").exists():
            return Path(p)
    return None

def fix_bundle(app_path=None):
    print(f"[Post-Build Fix] Starting target: {app_path or 'default'}...")
    
    site_pkgs = get_site_packages_path()
    if not site_pkgs:
        print("[Post-Build Fix] Could not find site-packages containing 'mlx'.")
        return
        
    app_dir = Path(app_path) if app_path else Path("dist/嘴炮輸入法.app")
    if not app_dir.exists():
        print(f"[Post-Build Fix] App bundle not found: {app_dir}")
        return

    # Target directories inside the bundle
    res_lib_dir = app_dir / "Contents/Resources/lib/python3.12"
    dyn_lib_dir = res_lib_dir / "lib-dynload"
    
    # 1. Copy the full mlx python module directory
    src_mlx = site_pkgs / "mlx"
    target_mlx = res_lib_dir / "mlx"
    
    if src_mlx.exists():
        print(f"[Post-Build Fix] Copying full 'mlx' source from {src_mlx} to {target_mlx}...")
        if target_mlx.exists():
            shutil.rmtree(target_mlx)
        shutil.copytree(src_mlx, target_mlx)
        # Ensure all files inside mlx are readable and executable
        for root, dirs, files in os.walk(target_mlx):
            for d in dirs: os.chmod(os.path.join(root, d), 0o755)
            for f in files: os.chmod(os.path.join(root, f), 0o755)
    else:
        print("[Post-Build Fix] Source mlx directory not found.")
        
    # The native extension looks for libmlx.dylib and metallib at @rpath, so it must be relative to where core.so sits
    target_dyn_mlx = dyn_lib_dir / "mlx"
    target_dyn_mlx_lib = target_dyn_mlx / "lib"
    src_lib_dir = src_mlx / "lib"
    
    if src_lib_dir.exists():
        print(f"[Post-Build Fix] Copying MLX native libraries (including metallib) to {target_dyn_mlx_lib}...")
        if target_dyn_mlx_lib.exists():
            shutil.rmtree(target_dyn_mlx_lib)
        shutil.copytree(src_lib_dir, target_dyn_mlx_lib)
        # Fix permissions for native dylibs and metallib
        for f in target_dyn_mlx_lib.glob("*"):
            os.chmod(f, 0o755)
    else:
        print(f"[Post-Build Fix] Could not find {src_lib_dir}")

    # 3. Fix Py2App grabbing x86_64 libssl under rosetta
    fw_dir = app_dir / "Contents" / "Frameworks"
    arm64_ssl = Path("/opt/homebrew/lib/libssl.3.dylib")
    arm64_crypto = Path("/opt/homebrew/lib/libcrypto.3.dylib")
    
    if fw_dir.exists() and arm64_ssl.exists() and arm64_crypto.exists():
        target_ssl = fw_dir / "libssl.3.dylib"
        target_crypto = fw_dir / "libcrypto.3.dylib"
        print("[Post-Build Fix] Patching OpenSSL with arm64 native slice...")
        if target_ssl.exists(): target_ssl.unlink()
        if target_crypto.exists(): target_crypto.unlink()
        shutil.copy2(arm64_ssl, target_ssl)
        shutil.copy2(arm64_crypto, target_crypto)
        # Explicitly set permissions for the Homebrew-sourced dylibs
        os.chmod(target_ssl, 0o755)
        os.chmod(target_crypto, 0o755)
        try:
            subprocess.run(
                ["install_name_tool", "-id", "@executable_path/../Frameworks/libcrypto.3.dylib", str(target_crypto)],
                check=True,
            )
            subprocess.run(
                ["install_name_tool", "-id", "@executable_path/../Frameworks/libssl.3.dylib", str(target_ssl)],
                check=True,
            )
            for old_ref in [
                "/opt/homebrew/opt/openssl@3/lib/libcrypto.3.dylib",
                "/opt/homebrew/Cellar/openssl@3/3.6.1/lib/libcrypto.3.dylib",
                "/opt/homebrew/Cellar/openssl@3/3.6.2/lib/libcrypto.3.dylib",
            ]:
                subprocess.run(
                    [
                        "install_name_tool",
                        "-change",
                        old_ref,
                        "@executable_path/../Frameworks/libcrypto.3.dylib",
                        str(target_ssl),
                    ],
                    check=False,
                )
        except Exception as e:
            print(f"[Post-Build Fix] OpenSSL install_name_tool patch skipped: {e}")

    print("[Post-Build Fix] Done!")

if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else None
    fix_bundle(target)
