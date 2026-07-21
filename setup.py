import sys
import os
import shutil
from setuptools import setup

# Increase recursion depth for complex dependency scanning in Python 3.12
sys.setrecursionlimit(5000)

APP = ['main.py']
DATA_FILES = [
    'assets',
    ('helpers', ['helpers/apple_local_llm']),
    ('soul/scenario', [
        'soul/scenario/default.md',
        'soul/scenario/情商大師.md',
        'soul/scenario/商務回應.md',
        'soul/scenario/社群貼文.md',
        'soul/scenario/逐字稿.md',
    ]),
    ('soul/format', [
        'soul/format/email.md',
        'soul/format/natural.md',
        'soul/format/social_post.md',
        'soul/format/formal_doc.md',
        'soul/format/slides.md',
    ]),
    'assets/fonts',
]

# ─── Site-packages path for namespace package workaround ───
SITE_PACKAGES = '/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/site-packages'

OPTIONS = {
    'argv_emulation': False,
    'arch': 'universal2',
    'strip': False,      # 禁止 py2app strip dylib，避免截斷導致 codesign 失敗
    'iconfile': 'assets/icon.icns',
    'plist': {
        'LSUIElement': False,  # 顯示 Dock 圖示以確保 TCC 權限攔截順利
        'CFBundleName': '嘴炮輸入法',
        'CFBundleDisplayName': '嘴炮輸入法',
        'CFBundleIdentifier': 'com.jimmy4tw.voicetype4tw-mac',
        'NSPrincipalClass': 'NSApplication',
        'CFBundleVersion': '2.9.18',
        'CFBundleShortVersionString': '2.9.18',
        'NSMicrophoneUsageDescription': 'VoiceType4TW requires microphone access for speech recognition.',
        'NSAccessibilityUsageDescription': '嘴炮輸入法需要輔助使用權限來監聽全域快捷鍵並自動貼上文字。',
        'NSAppleEventsUsageDescription': '嘴炮輸入法需要透過 AppleEvents 與其他程式互動以完成文字注入。',
        'NSSupportsAutomaticGraphicsSwitching': True,
        'NSHighResolutionCapable': True,
    },
    'packages': [
        # UI
        'rumps', 'PyQt6',
        # STT (mlx excluded - namespace package, copied manually post-build)
        'mlx_whisper',
        # Audio
        'sounddevice', '_sounddevice_data',
        # Network / LLM
        'httpx', 'certifi', 'opencc',
        # macOS Bridge
        'objc', 'Quartz',
        # Hotkey / Clipboard
        'pynput', 'pyperclip',
        # Image (Tray Icon)
        'PIL',
        # HuggingFace (model download at first launch)
        'huggingface_hub', 'tokenizers',
        # STT Math/Audio extensions
        'scipy',
    ],
    'includes': [
        'numpy',
        'mlx', 'mlx.core', 'mlx.nn', 'mlx.nn.layers',
        'mlx.optimizers', 'mlx.utils', 'mlx.extension',
        'mlx._reprlib_fix', 'mlx._distributed_utils'
    ],
    'excludes': [
        'tkinter', 'torch', 'tensorflow',
        'matplotlib', 'pandas',
        'IPython', 'jupyter', 'notebook',
        'PyInstaller', 'PySide6',
    ],
    # Tell py2app where to find mlx namespace package
    'site_packages': True,
}

setup(
    app=APP,
    name='嘴炮輸入法',
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
