"""
Modern VoiceType Settings Window using PyQt6.
Features tabs for General, STT/LLM, Vocab/Memory, and Stats.
"""
import sys
import os
import platform
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QStackedWidget, QLabel, QLineEdit, QComboBox, QCheckBox, QPushButton, 
    QTextEdit, QListWidget, QListWidgetItem, QTreeWidget, QTreeWidgetItem, QHeaderView,
    QMessageBox, QFileDialog, QScrollArea, QFrame, QSplitter, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QRect, QUrl, QTimer
from PyQt6.QtGui import QFont, QIcon, QColor, QPainter, QLinearGradient, QBrush, QPixmap, QDesktopServices
import shutil

import logging
from config import load_config, save_config
from paths import SOUL_BASE_PATH, SOUL_SCENARIO_DIR, SOUL_FORMAT_DIR, SOUL_TEMPLATE_DIR, BUILD_ID

log = logging.getLogger("voicetype.ui")
STT_ENGINES = ["local_whisper", "groq", "gemini", "openrouter"]
LLM_ENGINES = ["ollama", "openai", "claude", "openrouter", "gemini", "deepseek", "qwen"]
WHISPER_MODELS = ["tiny", "base", "small", "medium", "large"]
TRIGGER_MODES = ["push_to_talk", "toggle"]
HOTKEYS = ["right_option", "left_option", "right_ctrl", "f13", "f14", "f15"]
LLM_MODES = ["replace", "fast"]

from hotkey.listener import key_to_str, str_to_key


class GlassCard(QFrame):
    """A premium looking card with subtle border and background."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            GlassCard {
                background-color: rgba(45, 45, 55, 180);
                border: 1px solid rgba(255, 255, 255, 30);
                border-radius: 12px;
            }
        """)

class SidebarButton(QPushButton):
    def __init__(self, icon_text, label, index, on_click, parent=None):
        super().__init__(parent)
        self.index = index
        self.setCheckable(True)
        import platform
        font_family = "Taipei Sans TC Beta" if platform.system() == "Darwin" else "Microsoft JhengHei"
        self.setText(f"{icon_text}  {label}")
        self.setFont(QFont(font_family, 16, QFont.Weight.Medium))

        self.setFixedHeight(60)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(lambda: on_click(self.index))
        self.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #8a8d91;
                text-align: left;
                padding-left: 20px;
                border-radius: 12px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 10);
            }
            QPushButton:checked {
                background-color: #252a33;
                color: #7c4dff;
                font-weight: bold;
            }
        """)

class SNSButton(QPushButton):
    def __init__(self, icon_path, url, parent=None):
        super().__init__(parent)
        self.url = url
        self.setIcon(QIcon(icon_path))
        self.setIconSize(QSize(24, 24))
        self.setFixedSize(32, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("QPushButton { background: transparent; border: none; padding: 0; } QPushButton:hover { background: rgba(255,255,255,20); border-radius: 4px; }")
        self.clicked.connect(self._open_url)

    def _open_url(self):
        QDesktopServices.openUrl(QUrl(self.url))

CODE_TO_MAC_NAME = {
    61: "alt_r (Option右)",
    62: "ctrl_r (Control右)",
    60: "shift_r (Shift右)",
    54: "cmd_r (Command右)",
    55: "cmd (Command左)",
    56: "shift (Shift左)",
    59: "ctrl (Control左)",
    58: "alt (Option左)",
    63: "fn",
    116: "page_up",
    121: "page_down",
    115: "home",
    119: "end",
    117: "delete",
    114: "insert",
    123: "left",
    124: "right",
    125: "down",
    126: "up",
    53: "esc",
    105: "f13",
    107: "f14",
    113: "f15",
    106: "f16"
}

CODE_TO_WIN_NAME = {
    16: "shift",
    160: "shift_l (Shift 左)",
    161: "shift_r (Shift 右)",
    17: "ctrl",
    162: "ctrl_l (Ctrl 左)",
    163: "ctrl_r (Ctrl 右)",
    18: "alt",
    164: "alt_l (Alt 左)",
    165: "alt_r (Alt 右)",
    91: "win (Win左)",
    92: "win (Win右)",
    32: "space",
    13: "enter",
    27: "esc",
    20: "caps_lock",
    9: "tab",
    8: "backspace",
    46: "delete",
    33: "page_up",
    34: "page_down",
    35: "end",
    36: "home",
    37: "left",
    38: "up",
    39: "right",
    40: "down",
    45: "insert"
}

def translate_key_string(key_str):
    import re
    if not key_str:
        return "未設定"
    
    match = re.search(r'\(?code:(\d+)\)?', key_str, re.IGNORECASE)
    if not match:
        return key_str # fallback to literal if no code is present
        
    code = int(match.group(1))
    
    if platform.system() == "Windows":
        main_name = CODE_TO_WIN_NAME.get(code, f"Key {code}")
    else:
        main_name = CODE_TO_MAC_NAME.get(code, f"Key_{code}")
    
    parts = key_str.replace(f"(code:{code})", "").replace(f"code:{code}", "").split("+")
    mods = [p.strip() for p in parts if p.strip()]
    
    if mods:
        return f"{'+'.join(mods)} + {main_name}"
    return main_name

class HotkeyRecorderButton(QPushButton):
    """A button that captures the next key press to set a hotkey."""
    key_changed = pyqtSignal(str)

    def __init__(self, current_key_str, is_dark=True):
        super().__init__()
        self._key_str = current_key_str
        self._recording = False
        self._is_dark = is_dark
        self._update_text()
        self.clicked.connect(self._start_recording)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumHeight(32)

    @property
    def key_str(self):
        return self._key_str

    @key_str.setter
    def key_str(self, val):
        self._key_str = val
        self._update_text()

    def set_key(self, key_str):
        self.key_str = key_str

    def _update_text(self):
        if self._recording:
            self.setText("錄製中...")
            self.setStyleSheet("background: palette(highlight); color: white; border-radius: 6px;")
        else:
            display_text = translate_key_string(self._key_str) if self._key_str else "未設定"
            self.setText(display_text)
            self.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 10);
                    border: 1px solid rgba(255, 255, 255, 20);
                    color: #ddd;
                    border-radius: 6px;
                    padding-left: 10px;
                    text-align: left;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 15);
                }
            """)

    def _start_recording(self):
        self._recording = True
        self._update_text()
        self.setFocus()

    def keyPressEvent(self, event):
        if not self._recording:
            super().keyPressEvent(event)
            return
            
        try:
            key = event.key()
            modifiers = event.modifiers()
            native_code = event.nativeVirtualKey()
            
            # v2.8.27_V13: Request exact Left/Right modifier Virtual Keycode natively
            if platform.system() == "Windows":
                import ctypes
                user32 = ctypes.windll.user32
                if native_code == 18:
                    if user32.GetAsyncKeyState(164) & 0x8000: native_code = 164
                    elif user32.GetAsyncKeyState(165) & 0x8000: native_code = 165
                elif native_code == 17:
                    if user32.GetAsyncKeyState(162) & 0x8000: native_code = 162
                    elif user32.GetAsyncKeyState(163) & 0x8000: native_code = 163
                elif native_code == 16:
                    if user32.GetAsyncKeyState(160) & 0x8000: native_code = 160
                    elif user32.GetAsyncKeyState(161) & 0x8000: native_code = 161
            
            log.info(f"[recorder] Captured QtKey={key}, NativeCode={native_code}")
            
            # Capture native modifiers for Fn key support
            try:
                native_mods = event.nativeModifiers()
                is_fn = bool(native_mods & 0x800000) # kCGEventFlagMaskSecondaryFn
            except:
                is_fn = False
            
            # v2.8.17: Modifier-only hotkeys (e.g., single Right Ctrl, Right Cmd)
            # These are single-key modifier hotkeys that should record immediately
            SINGLE_MODIFIER_KEYS = {
                Qt.Key.Key_Control: "ctrl",
                Qt.Key.Key_Alt: "alt",
                Qt.Key.Key_Shift: "shift",
                Qt.Key.Key_Meta: "cmd",
                Qt.Key.Key_AltGr: "alt",
            }
            
            if key in SINGLE_MODIFIER_KEYS:
                # v2.8.24: Store purely as code:XX format
                self._key_str = f"code:{native_code}"
                self._recording = False
                self._update_text()
                self.key_changed.emit(self._key_str)
                self.clearFocus()
                log.info(f"[recorder] Recorded modifier key: {self._key_str}")
                return

            # For composite keys (e.g., Ctrl+A, Cmd+Shift+S)
            modifier_map = []
            if modifiers & Qt.KeyboardModifier.ControlModifier: modifier_map.append("ctrl")
            if modifiers & Qt.KeyboardModifier.AltModifier: modifier_map.append("alt")
            if modifiers & Qt.KeyboardModifier.ShiftModifier: modifier_map.append("shift")
            if modifiers & Qt.KeyboardModifier.MetaModifier: modifier_map.append("cmd")
            if is_fn: modifier_map.append("fn")
            
            # Use raw code for composite payload
            full_list = [m for m in modifier_map] + [f"code:{native_code}"]
            self._key_str = "+".join(full_list)
            
            self._recording = False
            self._update_text()
            self.key_changed.emit(self._key_str)
            self.clearFocus()
            log.info(f"[recorder] Recorded combo: {self._key_str}")
        except Exception as e:
            import traceback
            log.error(f"[recorder] Error in keyPressEvent: {e}\n{traceback.format_exc()}")
            self._recording = False
            self._update_text()
            self.clearFocus()
        else:
            pass  # keyAccepted


class PermissionLight(QWidget):
    def __init__(self, label_text, preference_url):
        super().__init__()
        self.url = preference_url
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)

        self.dot = QFrame()
        self.dot.setFixedSize(12, 12)
        self.dot.setStyleSheet("background-color: #555; border-radius: 6px;")
        layout.addWidget(self.dot)

        self.label = QLabel(label_text)
        win_font = "Microsoft JhengHei" if platform.system() == "Windows" else ""
        self.label.setStyleSheet(f"color: #e2e4e7; font-size: 14px; font-family: '{win_font}';")
        self.label.setWordWrap(True)
        layout.addWidget(self.label)


        layout.addStretch()

        self.fix_btn = QPushButton("設定")
        self.fix_btn.setFixedWidth(60)
        self.fix_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d333d;
                color: #8a8d91;
                font-size: 11px;
                padding: 2px 5px;
            }
            QPushButton:hover { background-color: #3d4452; color: #fff; }
        """)
        self.fix_btn.clicked.connect(self._open_preference)
        layout.addWidget(self.fix_btn)

    def _open_preference(self):
        import subprocess
        if platform.system() == "Windows":
            import os
            os.startfile(self.url)
        else:
            subprocess.run(["open", self.url])

    def set_status(self, authorized: bool):
        color = "#00e676" if authorized else "#ff5252"
        self.dot.setStyleSheet(f"background-color: {color}; border-radius: 6px;")
        status_text = " (已授權)" if authorized else " (未授權)"
        # Note: We keep the original label text and just update the color dot
        self.fix_btn.setVisible(not authorized)



class ModelStatusLight(QWidget):
    def __init__(self, model_name, size_info, desc_text):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.setSpacing(2)
        
        top_layout = QHBoxLayout()
        self.dot = QFrame()
        self.dot.setFixedSize(10, 10)
        self.dot.setStyleSheet("background-color: #555; border-radius: 5px;")
        top_layout.addWidget(self.dot)
        
        self.label = QLabel(f"{model_name} ({size_info})")
        win_font = "Microsoft JhengHei" if platform.system() == "Windows" else ""
        self.label.setStyleSheet(f"color: #e2e4e7; font-size: 13px; font-weight: bold; font-family: '{win_font}';")
        top_layout.addWidget(self.label)

        top_layout.addStretch()
        layout.addLayout(top_layout)
        
        self.desc = QLabel(desc_text)
        win_font = "Microsoft JhengHei" if platform.system() == "Windows" else ""
        self.desc.setStyleSheet(f"color: #888; font-size: 11px; margin-left: 18px; font-family: '{win_font}';")
        self.desc.setWordWrap(True)

        layout.addWidget(self.desc)

    def set_status(self, downloaded: bool):
        # 綠色代表已就緒，灰色代表未下載
        color = "#00e676" if downloaded else "#444"
        self.dot.setStyleSheet(f"background-color: {color}; border-radius: 5px;")


class SettingsWindow(QMainWindow):
    test_start = pyqtSignal()
    test_stop = pyqtSignal()
    test_toggle = pyqtSignal()
    test_llm = pyqtSignal()   # v2.8.15: LLM Mode hotkey test
    
    def __init__(self, on_save=None, start_page=0):
        super().__init__()
        self.config = load_config()
        self.on_save = on_save
        self._is_dark = True # Pro mode is dark by default
        
        # Windows: Ensure window is popped up and focused (but not always on top)
        if platform.system() == "Windows":
             # v2.8.27_V87: Explicitly set window icon via branding utility
             from utils.branding import apply_branding
             apply_branding(self)
             pass

        self._setup_ui()
        self._load_data()
        
        # 根據語言動態設定視窗標題
        from paths import VERSION_NAME
        lang = self.config.get("language", "zh")
        if "zh" in lang:
            win_font = "Microsoft JhengHei" if platform.system() == "Windows" else "Taipei Sans TC Beta"
            self.setFont(QFont(win_font))
            self.setWindowTitle(f"嘴炮輸入法 {VERSION_NAME}")
        else:
            self.setWindowTitle(f"VoiceType4TW {VERSION_NAME}")
        
        # 設定啟動頁面
        if 0 <= start_page < len(self.sidebar_buttons):
            # 延遲一點點執行，避免在 UI 還沒完全掛載時觸發 visibility 切換
            QTimer.singleShot(10, lambda: self._on_sidebar_changed(start_page))

    def _setup_ui(self):
        from paths import VERSION_NAME
        self.setWindowTitle(f"VoiceType4TW {VERSION_NAME}")
        self.setMinimumSize(900, 680)
        
        # Ensure it pops up correctly on Windows
        self.raise_()
        self.activateWindow()
        
        # Premium CSS
        win_font = "Microsoft JhengHei" if platform.system() == "Windows" else "PingFang TC"
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0f1115;
            }
            QWidget#sidebar_container {
                background-color: #16191f;
                border-right: 1px solid #252a33;
            }
            QStackedWidget {
                background-color: #0f1115;
            }
            QListWidget#sidebar {
                background: transparent;
                border: none;
                outline: none;
                padding: 15px;
            }
            QListWidget#sidebar::item {
                padding: 20px;
                color: #8a8d91;
                border-radius: 12px;
                margin-bottom: 10px;
            }
            QListWidget#sidebar::item:selected {
                background-color: #252a33;
                color: #7c4dff;
                font-weight: bold;
            }
            QLabel {
                color: #e2e4e7;
                font-family: '""" + win_font + """';
            }
            QLineEdit, QComboBox, QTextEdit, QListWidget, QTreeWidget {
                font-family: '""" + win_font + """';
                background-color: #1c1f26;
                border: 1px solid #2d333d;
                border-radius: 8px;
                color: #e2e4e7;
                padding: 8px;
                selection-background-color: #3d4452;
            }
            /* 強制選單彈出框也是深色 */
            QAbstractItemView {
                background-color: #1c1f26;
                color: #e2e4e7;
                border: 1px solid #2d333d;
                selection-background-color: #3d4452;
                outline: none;
            }
            QTreeWidget::item { padding: 4px; }
            QHeaderView::section {
                background-color: #1c1f26;
                color: #8a8d91;
                padding: 6px;
                border: none;
                font-weight: bold;
            }
            QPushButton {
                background-color: #7c4dff;
                color: white;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover { background-color: #9575cd; }
            QPushButton#secondary {
                background-color: #2d333d;
                color: #e2e4e7;
            }
            QPushButton#danger {
                background-color: transparent;
                border: 1px solid #ff5252;
                color: #ff5252;
            }
            QPushButton#danger:hover {
                background-color: #ff5252;
                color: white;
            }
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 6px;
            }
            QScrollBar::handle:vertical {
                background: #3d3d4d;
                border-radius: 3px;
                min-height: 20px;
            }
            QCheckBox { color: #e2e4e7; spacing: 10px; }
            QCheckBox::indicator { width: 18px; height: 18px; }
        """)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        sidebar_container = QWidget()
        sidebar_container.setObjectName("sidebar_container")
        sidebar_container.setFixedWidth(300)
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        
        logo_container = QWidget()
        logo_vbox = QVBoxLayout(logo_container)
        logo_vbox.setContentsMargins(0, 50, 0, 0) # Apply 50px Margin Top
        logo_vbox.setSpacing(0)
        
        lbl_en = QLabel("VoiceType4TW")
        lbl_en.setStyleSheet("font-family: 'Myriad Pro'; font-weight: bold; font-size: 28px; color: white;")
        lbl_en.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_en = QLabel("VoiceType4TW")
        lbl_en.setStyleSheet("font-family: 'Myriad Pro'; font-weight: bold; font-size: 28px; color: white;")
        lbl_en.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        from paths import VERSION_NAME
        os_ver = f"Windows Version" if platform.system() == "Windows" else f"macOS Version "
        lbl_os = QLabel(os_ver)
        lbl_os.setStyleSheet("font-family: 'Myriad Pro'; font-style: italic; font-size: 12px; color: #8a8d91;")
        lbl_os.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        logo_vbox.addWidget(lbl_en)
        logo_vbox.addWidget(lbl_os)
        sidebar_layout.addWidget(logo_container)

        # Menu List - Use Layout instead of QListWidget for perfect visibility
        self.menu_group = QWidget()
        self.menu_layout = QVBoxLayout(self.menu_group)
        self.menu_layout.setContentsMargins(10, 20, 10, 0)
        self.menu_layout.setSpacing(5)
        
        self.sidebar_buttons = []
        menus = [
            ("🏠", "Dashboard"),
            ("🎙", "辨識 & AI"),
            ("✨", "靈魂設定"),
            ("📚", "詞彙 & 記憶"),
            ("☁️", "雲端同步"),
            ("📊", "數據統計"),
            ("⚙️", "系統設定")
        ]
        
        for i, (icon, label) in enumerate(menus):
            btn = SidebarButton(icon, label, i, self._on_sidebar_changed)
            self.menu_layout.addWidget(btn)
            self.sidebar_buttons.append(btn)
        
        self.sidebar_buttons[0].setChecked(True) # Default
        sidebar_layout.addWidget(self.menu_group)
        
        sidebar_layout.addStretch()
        
        # Credits and SNS at Bottom
        from paths import VERSION_NAME, BUILD_ID
        credit_box = QLabel(f"{VERSION_NAME} |\n{BUILD_ID}\n\n主要開發者：吉米丘, CC58TW\n協助開發者：Gemini, Nebula")
        credit_box.setStyleSheet("color: #555; font-size: 10px; margin-left: 25px; line-height: 1.2;")
        sidebar_layout.addWidget(credit_box)
        
        sns_container = QWidget()
        sns_layout = QHBoxLayout(sns_container)
        sns_layout.setContentsMargins(25, 5, 25, 20) # Left align with credit box
        sns_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        sns_layout.setSpacing(10)
        
        _assets_dir = str(Path(__file__).parent.parent / "assets")
        sns_links = [
            (os.path.join(_assets_dir, "sns-youtube.png"), "https://youtube.com/@Jimmy4TW"),
            (os.path.join(_assets_dir, "sns-facebook.png"), "https://www.facebook.com/acykjcms"),
            (os.path.join(_assets_dir, "sns-instagram.png"), "https://www.instagram.com/jimmy4tw/"),
            (os.path.join(_assets_dir, "sns-tiktok.png"), "https://www.tiktok.com/@jimmy4tw"),
            (os.path.join(_assets_dir, "sns-threads.png"), "https://www.threads.net/@jimmy4tw"),
            (os.path.join(_assets_dir, "sns-4tw.png"), "https://Jimmy4.TW/")
        ]
        
        for icon_path, url in sns_links:
            btn = SNSButton(icon_path, url)
            sns_layout.addWidget(btn)
        
        sidebar_layout.addWidget(sns_container)
        
        main_layout.addWidget(sidebar_container)

        # Content Area
        content_container = QWidget()
        self.content_layout = QVBoxLayout(content_container)
        self.content_layout.setContentsMargins(40, 50, 40, 40) # 50px Top Margin
        
        self.stack = QStackedWidget()
        self.content_layout.addWidget(self.stack)

        # Pages
        self.stack.addWidget(self._create_dashboard_page())
        self.stack.addWidget(self._create_stt_llm_page())
        self.stack.addWidget(self._create_soul_page())
        self.stack.addWidget(self._create_vocab_mem_page())
        self.stack.addWidget(self._create_sync_page())
        self.stack.addWidget(self._create_stats_page())
        self.stack.addWidget(self._create_general_page())

        # Footer Actions (Grouped for visibility control)
        self.footer_widget = QWidget()
        footer = QHBoxLayout(self.footer_widget)
        footer.setContentsMargins(0, 20, 0, 0)
        self.btn_save = QPushButton("儲存設定")
        self.btn_save.clicked.connect(self._save_action)
        self.btn_cancel = QPushButton("放棄設定")
        self.btn_cancel.setObjectName("secondary")
        self.btn_cancel.clicked.connect(self.close)
        
        footer.addStretch()
        footer.addWidget(self.btn_cancel)
        footer.addWidget(self.btn_save)
        self.content_layout.addWidget(self.footer_widget)
        
        # Initial footer visibility
        self._on_sidebar_changed(0)

        main_layout.addWidget(content_container)

    def _on_sidebar_changed(self, idx):
        # Update button states
        for i, btn in enumerate(self.sidebar_buttons):
            btn.setChecked(i == idx)
        
        self.stack.setCurrentIndex(idx)
        # Dashboard (0) and Stats (5) hide save buttons
        self.footer_widget.setVisible(idx not in [0, 5])

    def _create_sync_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        # Shift everything UP
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        layout.addWidget(self._page_section_header("☁️ 雲端同步 & NAS (Cross-Platform Sync)"))
        
        desc = QLabel(
            "透過設定同步目錄，您可以在多台 Mac 或 PC 之間共用「靈魂情境」、「詞彙」與「AI 記憶」。\n"
            "建議選擇您的 NAS 同步資料夾、iCloud 或 Google Drive 目錄。\n\n"
            "※ 注意：本機「控制熱鍵」與硬體偏好設定仍會保持各機獨立，不會互相干擾。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #8a8d91; line-height: 1.6; font-size: 14px;")
        layout.addWidget(desc)

        sync_panel = QFrame()
        sync_panel.setStyleSheet("""
            QFrame {
                background-color: rgba(124, 77, 255, 15); 
                border: 1px solid rgba(124, 77, 255, 40); 
                border-radius: 12px; 
            }
        """)
        sync_layout = QVBoxLayout(sync_panel)
        sync_layout.setContentsMargins(25, 25, 25, 25)
        sync_layout.setSpacing(20)
        
        self.sync_status_lbl = QLabel("目前狀態：本地存儲 (Local Only)")
        self.sync_status_lbl.setStyleSheet("color: #ccc; font-weight: bold; font-size: 16px;")
        sync_layout.addWidget(self.sync_status_lbl)
        
        sync_btns = QHBoxLayout()
        self.btn_set_sync_dir = QPushButton("🔗 連結同步目錄 (Connect Sync Folder)")
        self.btn_set_sync_dir.setMinimumHeight(45)
        self.btn_set_sync_dir.clicked.connect(self._set_sync_directory)
        sync_btns.addWidget(self.btn_set_sync_dir)
        
        self.btn_clear_sync = QPushButton("🔌 取消同步")
        self.btn_clear_sync.setObjectName("danger")
        self.btn_clear_sync.setFixedWidth(130)
        self.btn_clear_sync.setMinimumHeight(45)
        self.btn_clear_sync.clicked.connect(self._clear_sync_directory)
        sync_btns.addWidget(self.btn_clear_sync)
        sync_layout.addLayout(sync_btns)
        
        from paths import SYNC_POINTER_PATH
        if SYNC_POINTER_PATH.exists():
            try:
                path_str = SYNC_POINTER_PATH.read_text(encoding="utf-8").strip()
                if path_str:
                    self.sync_status_lbl.setText(f"✅ 已連結同步：{path_str}")
                    self.sync_status_lbl.setStyleSheet("color: #00e676; font-weight: bold; font-size: 16px;")
            except: pass

        layout.addWidget(sync_panel)
        
        warning_box = GlassCard()
        w_layout = QVBoxLayout(warning_box)
        w_layout.setContentsMargins(15, 15, 15, 15)
        w_lbl = QLabel("🛡️ 安全性提醒：同步目錄包含您的 AI API Key 設定，請確保該空間僅由您本人存取。")
        w_lbl.setStyleSheet("color: #ffab40; font-size: 13px;")
        w_lbl.setWordWrap(True)
        w_layout.addWidget(w_lbl)
        layout.addWidget(warning_box)

        layout.addStretch()
        return page

    def _create_dashboard_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        # Shift everything UP: significantly reduce top margin
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(30)

        dash_header = QHBoxLayout()
        header = QLabel("Dashboard")
        header.setStyleSheet("font-size: 28px; font-weight: bold; color: #ffffff;")
        dash_header.addWidget(header)
        
        dash_header.addStretch()
        
        title_cn = QLabel("嘴炮輸入法")
        win_font = "Microsoft JhengHei" if platform.system() == "Windows" else "Taipei Sans TC Beta"
        title_cn.setStyleSheet(f"font-family: '{win_font}'; font-size: 32px; font-weight: bold; color: #ffffff;")
        dash_header.addWidget(title_cn)

        
        # Add side margins to content but not to the header text alignment if needed
        dash_header_container = QWidget()
        dash_header_v = QVBoxLayout(dash_header_container)
        dash_header_v.setContentsMargins(0, 0, 0, 0) # Tight
        dash_header_v.addLayout(dash_header)
        layout.addWidget(dash_header_container)

        # Top Cards: Row 1
        cards_row1 = QHBoxLayout()
        cards_row1.setSpacing(15)
        
        # 1. Permission / System Environment Card
        if platform.system() == "Windows":
            # Windows: 顯示 GPU/CUDA 與麥克風資訊
            env_card = GlassCard()
            p_layout = QVBoxLayout(env_card)
            p_layout.setContentsMargins(15, 15, 15, 15)
            lbl_p = QLabel("🖥️ 系統環境")
            lbl_p.setStyleSheet("font-weight: bold; color: #aaa; margin-bottom: 5px;")
            p_layout.addWidget(lbl_p)
            
            # GPU / CUDA 偵測 (v2.8.27_V28: Robust check)
            gpu_text = "⏳ 偵測中..."
            cuda_color = "#888"
            try:
                # 優先檢查是否已有全域載入的 STT 實例可用於查詢
                # 我們可以透過 QApplication 獲取主 App 實例的高級方法
                # 或者直接嘗試導入 (現在有 libiomp5md.dll 了應該安全)
                import ctranslate2
                try:
                    cuda_count = ctranslate2.get_cuda_device_count()
                    if cuda_count > 0:
                        gpu_text = f"✅ CUDA GPU × {cuda_count} (加速可用)"
                        cuda_color = "#00e676"
                    else:
                        gpu_text = "⚠️ 未偵測到 CUDA GPU (CPU 模式)"
                        cuda_color = "#ffab40"
                except Exception as _inner_e:
                    log.warning(f"[ui] get_cuda_device_count failed: {_inner_e}")
                    gpu_text = "⚠️ GPU 偵測組件異常"
                    cuda_color = "#ffab40"
            except Exception as e:
                log.error(f"[ui] ctranslate2 import error in dashboard: {e}")
                gpu_text = "❌ 驅動組件遺失 (V28)"
                cuda_color = "#ff5252"
            
            self.lbl_gpu = QLabel(gpu_text)
            win_font = "Microsoft JhengHei" if platform.system() == "Windows" else ""
            self.lbl_gpu.setStyleSheet(f"color: {cuda_color}; font-size: 14px; font-weight: bold; font-family: '{win_font}';")
            self.lbl_gpu.setWordWrap(True)
            p_layout.addWidget(self.lbl_gpu)

            
            # 麥克風裝置偵測
            mic_text = "未知裝置"
            try:
                import sounddevice
                dev = sounddevice.query_devices(kind='input')
                mic_text = dev.get('name', '未知裝置')
            except Exception:
                mic_text = "無法偵測"
            
            self.lbl_mic_device = QLabel(f"🎤 {mic_text}")
            win_font = "Microsoft JhengHei" if platform.system() == "Windows" else ""
            self.lbl_mic_device.setStyleSheet(f"color: #e2e4e7; font-size: 13px; font-family: '{win_font}';")
            self.lbl_mic_device.setWordWrap(True)

            p_layout.addWidget(self.lbl_mic_device)
            
            cards_row1.addWidget(env_card)
            
            # 建立隱藏的權限燈號（讓 _check_all_permissions 不炸）
            self.light_acc = PermissionLight("輔助功能", "")
            self.light_acc.hide()
            self.light_input = PermissionLight("輸入監聽", "")
            self.light_input.hide()
            self.light_mic = PermissionLight("麥克風", "")
            self.light_mic.hide()

        # 2. Model Card (New)
        model_card = GlassCard()
        m_layout = QVBoxLayout(model_card)
        m_layout.setContentsMargins(15, 15, 15, 15)
        lbl_m = QLabel("🧠 AI 本地模型 (Faster-Whisper)")
        lbl_m.setStyleSheet("font-weight: bold; color: #aaa; margin-bottom: 5px;")
        m_layout.addWidget(lbl_m)
        
        self.light_model_small = ModelStatusLight("Small", "500MB", "輕快，但精準度稍遜。")
        self.light_model_medium = ModelStatusLight("Medium", "1.5GB", "均衡型，首選推薦 (精準)。")
        self.light_model_large = ModelStatusLight("Large", "3.0GB", "極致精準，背景嘈雜也能辨識。")
        m_layout.addWidget(self.light_model_small)
        m_layout.addWidget(self.light_model_medium)
        m_layout.addWidget(self.light_model_large)
        cards_row1.addWidget(model_card)

        # 3. Status Card
        status_card = GlassCard()
        status_layout = QVBoxLayout(status_card)
        status_layout.setContentsMargins(15, 15, 15, 15)
        lbl_s = QLabel("📺 運行狀態")
        lbl_s.setStyleSheet("font-weight: bold; color: #aaa; margin-bottom: 5px;")
        status_layout.addWidget(lbl_s)
        
        self.lbl_status_ai = QLabel("AI 潤飾: 已開啟")
        self.lbl_status_ai.setStyleSheet("color: #7c4dff; font-weight: bold; font-size: 16px;")
        status_layout.addWidget(self.lbl_status_ai)
        
        self.lbl_status_stt = QLabel("引擎: Local Whisper")
        self.lbl_status_stt.setStyleSheet("color: #888; font-size: 13px;")
        status_layout.addWidget(self.lbl_status_stt)
        cards_row1.addWidget(status_card)

        layout.addLayout(cards_row1)

        # Bottom Cards: Row 2
        cards_row2 = QHBoxLayout()

        # 3. Quick Stats Card
        stats_card = GlassCard()
        sq_layout = QVBoxLayout(stats_card)
        sq_layout.setContentsMargins(20, 20, 20, 20)
        sq_layout.addWidget(QLabel("今日語效"))
        self.lbl_today_count = QLabel("0 次錄音")
        self.lbl_today_count.setStyleSheet("color: #00e5ff; font-weight: bold; font-size: 16px;")
        sq_layout.addWidget(self.lbl_today_count)
        self.lbl_today_chars = QLabel("錄製約 0 字")
        sq_layout.addWidget(self.lbl_today_chars)
        cards_row2.addWidget(stats_card)

        # 4. Time Saved Card
        time_card = GlassCard()
        t_layout = QVBoxLayout(time_card)
        t_layout.setContentsMargins(20, 20, 20, 20)
        t_layout.addWidget(QLabel("累計省下時間"))
        self.lbl_time_saved = QLabel("0 分鐘")
        self.lbl_time_saved.setStyleSheet("color: #ffab40; font-weight: bold; font-size: 16px;")
        t_layout.addWidget(self.lbl_time_saved)
        self.lbl_total_chars_desc = QLabel("共辨識 0 字")
        self.lbl_total_chars_desc.setStyleSheet("color: #888; font-size: 13px;")
        t_layout.addWidget(self.lbl_total_chars_desc)
        cards_row2.addWidget(time_card)
        
        layout.addLayout(cards_row2)

        # ── Model Download Progress Card ──────────────────────
        from PyQt6.QtWidgets import QProgressBar
        self.download_card = GlassCard()
        dl_layout = QVBoxLayout(self.download_card)
        dl_layout.setContentsMargins(20, 20, 20, 20)
        dl_layout.addWidget(QLabel("⬇️ 模型下載進度"))
        
        self.lbl_download_status = QLabel("等待模型載入...")
        self.lbl_download_status.setStyleSheet("color: #00e5ff; font-size: 14px; font-weight: bold;")
        dl_layout.addWidget(self.lbl_download_status)
        
        self.download_progress = QProgressBar()
        self.download_progress.setRange(0, 0)  # 不確定進度 → 跑馬燈模式
        self.download_progress.setFixedHeight(8)
        self.download_progress.setStyleSheet("""
            QProgressBar { background: #1c1f26; border: 1px solid #2d333d; border-radius: 4px; }
            QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7c4dff, stop:1 #00e5ff); border-radius: 4px; }
        """)
        dl_layout.addWidget(self.download_progress)
        
        self.lbl_download_detail = QLabel("首次啟動需要下載 AI 模型，請確保網路暢通。")
        self.lbl_download_detail.setStyleSheet("color: #666; font-size: 11px;")
        dl_layout.addWidget(self.lbl_download_detail)
        
        layout.addWidget(self.download_card)
        # 預設隱藏：有模型就不需要看到
        self.download_card.setVisible(not self._is_model_present(self.config.get("whisper_model", "medium")))

        # Recent Activity Card
        recent_card = GlassCard()
        rc_layout = QVBoxLayout(recent_card)
        rc_layout.setContentsMargins(20, 20, 20, 20)
        rc_layout.addWidget(QLabel("💡 最近學到的詞彙"))
        self.dashboard_vocab = QListWidget()
        self.dashboard_vocab.setStyleSheet("background: transparent; border: none; font-size: 13px;")
        self.dashboard_vocab.setFixedHeight(120)
        rc_layout.addWidget(self.dashboard_vocab)
        layout.addWidget(recent_card)

        layout.addStretch()
        return page

    def _create_stt_llm_page(self):
        page = QScrollArea()
        page.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(25)

        layout.addWidget(self._page_section_header("🎙 語音辨識配置"))
        self.stt_engine = self._add_grid_row(layout, "核心引擎", QComboBox())
        engine_meta = {
            "local_whisper": "Local Whisper (RTX顯卡加速, 也支援 CPU/GPU)",
            "groq":          "Groq Whisper (神級雲端超極速)",
            "gemini":        "Gemini (雲端 API)",
            "openrouter":    "OpenRouter (雲端 API)",
        }
        for eng in STT_ENGINES:
            self.stt_engine.addItem(engine_meta.get(eng, eng), eng)
        
        self.whisper_model = self._add_grid_row(layout, "Whisper 規格", QComboBox())
        self._populate_whisper_models()

        self.groq_key = self._add_grid_row(layout, "Groq API Key (選填)", QLineEdit())
        self.groq_key.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.language = self._add_grid_row(layout, "優先辨識語言", QComboBox())
        lang_meta = {
            "zh": "繁體中文",
            "en": "英文",
            "ja": "日文",
            "ko": "韓文",
            "yue": "粵語",
            "auto": "自動偵測"
        }
        for code, name in lang_meta.items():
            self.language.addItem(f"{name} ({code})", code)

        layout.addWidget(self._page_section_header("🤖 大語言模型潤飾 (LLM) 配置"))
        self.llm_enabled = QCheckBox("啟用高階智慧潤飾與翻譯")
        layout.addWidget(self.llm_enabled)

        self.llm_engine = self._add_grid_row(layout, "模型提供者", QComboBox())
        self.llm_engine.addItems(LLM_ENGINES)

        self.llm_mode = self._add_grid_row(layout, "內容注入模式", QComboBox())
        self.llm_mode.addItems(LLM_MODES)

        # API Keys
        self.openai_key = self._add_grid_row(layout, "OpenAI API Key", QLineEdit())
        self.openai_key.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.anthropic_key = self._add_grid_row(layout, "Anthropic (Claude) Key", QLineEdit())
        self.anthropic_key.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.gemini_key = self._add_grid_row(layout, "Gemini API Key", QLineEdit())
        self.gemini_key.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.openrouter_key = self._add_grid_row(layout, "OpenRouter API Key", QLineEdit())
        self.openrouter_key.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.qwen_key = self._add_grid_row(layout, "通義千問 (Qwen) Key", QLineEdit())
        self.qwen_key.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.deepseek_key = self._add_grid_row(layout, "DeepSeek API Key", QLineEdit())
        self.deepseek_key.setEchoMode(QLineEdit.EchoMode.Password)

        layout.addWidget(self._page_section_header("🪄 AI 魔術指令與展示選項"))
        self.magic_trigger = self._add_grid_row(layout, "啟動咒語 (例如: 嘿 助理)", QLineEdit())
        self.magic_trigger.setPlaceholderText("預設為: 嘿 VoiceType")
        
        self.debug_showcase_mode_llm = QLabel("💡 提示：展示模式與 Demo 模式已移至「系統設定」分頁。")
        self.debug_showcase_mode_llm.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.debug_showcase_mode_llm)

        container.setLayout(layout)
        page.setWidget(container)
        return page

    def _create_soul_page(self):
        from PyQt6.QtWidgets import QTabWidget
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)

        layout.addWidget(self._page_section_header("✨ AI 靈魂與情境治理"))
        
        self.soul_tabs = QTabWidget()
        self.soul_tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid rgba(255,255,255,10); border-radius: 8px; background: rgba(30,30,40,100); }
            QTabBar::tab { background: transparent; color: #8a8d91; padding: 10px 20px; font-size: 14px; }
            QTabBar::tab:selected { color: #7c4dff; border-bottom: 2px solid #7c4dff; font-weight: bold; }
        """)
        
        # 1. 基底靈魂
        base_tab = QWidget()
        base_layout = QVBoxLayout(base_tab)
        self.soul_prompt = QTextEdit()
        self.soul_prompt.setFont(QFont("Monaco", 12))
        self.soul_prompt.setPlaceholderText("輸入 AI 的基底靈魂提示詞 (人格、風格、去贅詞規則)...")
        self.soul_prompt.setStyleSheet("background: rgba(20,20,30,150); border: 1px solid rgba(255,255,255,10); border-radius: 8px; color: #eee;")
        base_layout.addWidget(self.soul_prompt)
        self.soul_tabs.addTab(base_tab, "🏠 基底靈魂")

        # 2. 情境瀏覽 (v2.7.32: 改名為性格模式)
        scenario_tab = self._create_file_list_tab(SOUL_SCENARIO_DIR, "這裡存放不同場景的提示詞（性格模式），例如：社群貼文、商務回應。") #咖啡版功能
        self.soul_tabs.addTab(scenario_tab, "🎭 性格模式") #咖啡版功能

        # 3. 格式瀏覽 (v2.7.32: 隱藏)
        # format_tab = self._create_file_list_tab(SOUL_FORMAT_DIR, "這裡決定輸出的格式。")
        # self.soul_tabs.addTab(format_tab, "📝 輸出格式")

        # 4. 模板管理 (v2.7.32: 隱藏)
        # template_tab = self._create_file_list_tab(SOUL_TEMPLATE_DIR, "這裡存放儲存過的範例。")
        # self.soul_tabs.addTab(template_tab, "📌 我的模板")

        layout.addWidget(self.soul_tabs)
        return page

    def _create_file_list_tab(self, directory: Path, desc: str, is_json: bool = False):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 頂部操作區
        controls_layout = QVBoxLayout()
        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet("color: #888; font-size: 12px;")
        controls_layout.addWidget(desc_lbl)
        
        create_layout = QHBoxLayout()
        new_item_name = QLineEdit()
        new_item_name.setPlaceholderText("輸入新項目名稱...")
        new_item_name.setStyleSheet("background: rgba(0,0,0,50); border: 1px solid #444; border-radius: 4px; padding: 4px; color: #fff;")
        
        btn_add = QPushButton("➕ 新增項目")
        btn_add.setFixedWidth(100)
        btn_add.setStyleSheet("background: #2e7d32; color: white; padding: 5px; border-radius: 4px;")
        
        btn_del = QPushButton("🗑 刪除所選")
        btn_del.setFixedWidth(100)
        btn_del.setStyleSheet("background: #c62828; color: white; padding: 5px; border-radius: 4px;")
        
        create_layout.addWidget(new_item_name)
        create_layout.addWidget(btn_add)
        create_layout.addWidget(btn_del)
        controls_layout.addLayout(create_layout)
        
        layout.addLayout(controls_layout)
        
        lst = QListWidget()
        lst.setStyleSheet("background: rgba(20,20,30,150); border: 1px solid rgba(255,255,255,10); border-radius: 8px; color: #eee;")
        layout.addWidget(lst)
        
        def refresh():
            lst.clear()
            if not directory.exists(): return
            ext = "*.json" if is_json else "*.md"
            for f in sorted(directory.glob(ext)):
                if f.name == "default.md": continue # v2.7.32: 隱藏預設靈魂以免使用者誤改
                lst.addItem(f.name)
        
        QTimer.singleShot(100, refresh)
        
        # 內容編輯區 (不再是純預覽，改為可編輯)
        layout.addWidget(QLabel("內容編輯："))
        editor = QTextEdit()
        editor.setFont(QFont("Monaco", 11))
        editor.setStyleSheet("background: rgba(40,40,50,150); color: #fff; border: 1px solid rgba(255,255,255,20); border-radius: 8px;")
        layout.addWidget(editor)
        
        btn_save = QPushButton("💾 儲存修改")
        btn_save.setStyleSheet("background: #7c4dff; color: white; padding: 10px; border-radius: 6px; font-weight: bold;")
        btn_save.hide() # 初始隱藏
        layout.addWidget(btn_save)
        
        def on_item_clicked(item):
            fpath = directory / item.text()
            if fpath.exists():
                text = fpath.read_text(encoding="utf-8")
                if is_json:
                    import json
                    try:
                        data = json.loads(text)
                        text = json.dumps(data, indent=2, ensure_ascii=False)
                    except: pass
                editor.setPlainText(text)
                btn_save.show()
        
        def on_save():
            item = lst.currentItem()
            if not item: return
            fpath = directory / item.text()
            try:
                fpath.write_text(editor.toPlainText(), encoding="utf-8")
                QMessageBox.information(self, "成功", f"「{item.text()}」已儲存。")
            except Exception as e:
                QMessageBox.critical(self, "錯誤", f"儲存失敗：{e}")
        
        def on_add():
            name = new_item_name.text().strip()
            if not name:
                QMessageBox.warning(self, "提示", "請輸入項目名稱。")
                return
            
            filename = f"{name}.json" if is_json else f"{name}.md"
            fpath = directory / filename
            if fpath.exists():
                QMessageBox.warning(self, "警告", "名稱已存在！")
                return
            
            try:
                fpath.write_text("# 新項目\n在此輸入設定...", encoding="utf-8")
                new_item_name.clear()
                refresh()
                # 選中新項目
                items = lst.findItems(filename, Qt.MatchFlag.MatchExactly)
                if items:
                    lst.setCurrentItem(items[0])
                    on_item_clicked(items[0])
            except Exception as e:
                QMessageBox.critical(self, "錯誤", f"建立失敗：{e}")

        def on_delete():
            item = lst.currentItem()
            if not item: return
            reply = QMessageBox.question(self, "確認刪除", f"確定要刪除「{item.text()}」嗎？", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                (directory / item.text()).unlink()
                refresh()
                editor.clear()
                btn_save.hide()

        lst.itemClicked.connect(on_item_clicked)
        btn_add.clicked.connect(on_add)
        btn_del.clicked.connect(on_delete)
        btn_save.clicked.connect(on_save)
        
        btn_open = QPushButton("📂 在 Finder 中打開資料夾")
        btn_open.setStyleSheet("background: transparent; border: 1px solid #3d4452; color: #888; font-size: 11px;")
        btn_open.clicked.connect(lambda: os.system(f"open '{directory}'"))
        layout.addWidget(btn_open)

        return tab

    def _create_vocab_mem_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # Left: Vocab
        v_box = QWidget()
        v_layout = QVBoxLayout(v_box)
        v_layout.addWidget(QLabel("✏️ 私人詞庫"))
        self.vocab_list = QListWidget()
        v_layout.addWidget(self.vocab_list)
        
        vh = QHBoxLayout()
        self.vocab_input = QLineEdit()
        self.vocab_input.setPlaceholderText("新增...")
        self.btn_add_vocab = QPushButton("+")
        self.btn_add_vocab.setFixedWidth(50)
        self.btn_add_vocab.clicked.connect(self._add_vocab)
        vh.addWidget(self.vocab_input)
        vh.addWidget(self.btn_add_vocab)
        v_layout.addLayout(vh)
        
        self.btn_del_vocab = QPushButton("刪除已選")
        self.btn_del_vocab.setObjectName("danger")
        self.btn_del_vocab.clicked.connect(self._del_vocab)
        v_layout.addWidget(self.btn_del_vocab)

        # Right: Learned & Memory
        right_box = QWidget()
        rl = QVBoxLayout(right_box)
        
        rl.addWidget(QLabel("💡 AI 學習清單"))
        self.learned_list = QListWidget()
        rl.addWidget(self.learned_list)
        lh = QHBoxLayout()
        self.btn_promote = QPushButton("升格自訂")
        self.btn_promote.clicked.connect(self._promote_vocab)
        lh.addWidget(self.btn_promote)
        self.btn_delete_learned = QPushButton("刪除")
        self.btn_delete_learned.setObjectName("danger")
        self.btn_delete_learned.setFixedHeight(32)
        self.btn_delete_learned.clicked.connect(self._delete_learned_word)
        lh.addWidget(self.btn_delete_learned)
        rl.addLayout(lh)

        rl.addWidget(QLabel("🧠 長期記憶"))
        self.mem_tree = QTreeWidget()
        self.mem_tree.setHeaderLabels(["時間", "快照"])
        rl.addWidget(self.mem_tree)

        mem_ctrl_row = QHBoxLayout()
        self.memory_inject_cb = QCheckBox("注入 LLM 記憶")
        self.memory_inject_cb.setChecked(False)
        mem_ctrl_row.addWidget(self.memory_inject_cb)
        mem_ctrl_row.addStretch()
        self.btn_purge_memory = QPushButton("壓縮本週記憶")
        self.btn_purge_memory.setObjectName("danger")
        self.btn_purge_memory.setFixedHeight(32)
        self.btn_purge_memory.clicked.connect(self._purge_memory)
        mem_ctrl_row.addWidget(self.btn_purge_memory)
        rl.addLayout(mem_ctrl_row)

        splitter.addWidget(v_box)
        splitter.addWidget(right_box)
        return page

    def _create_stats_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(self._page_section_header("詳細分析數據"))
        
        self.stats_tree = QTreeWidget()
        self.stats_tree.setHeaderLabels(["範圍", "對話數", "語音長度", "轉錄字數", "省下時間"])
        layout.addWidget(self.stats_tree)
        
        self.btn_refresh_stats = QPushButton("重新整理數據")
        self.btn_refresh_stats.setObjectName("secondary")
        self.btn_refresh_stats.clicked.connect(self._refresh_stats)
        layout.addWidget(self.btn_refresh_stats)
        
        layout.addStretch()
        return page

    def _create_general_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        layout.addWidget(self._page_section_header("⌨️ 設定錄音按鍵"))
        
        hotkey_grid = QFrame()
        grid_layout = QVBoxLayout(hotkey_grid)
        
        row_ptt = QHBoxLayout()
        self.btn_ptt = HotkeyRecorderButton(self.config.get("hotkey_ptt", "alt_r"))
        self.btn_ptt.setFixedHeight(32)
        # v2.9.1: Fixed width so it's not too long and doesn't overlap
        self.btn_ptt.setFixedWidth(160)
        
        self.btn_test_rec = QPushButton("🚀 測試")
        self.btn_test_rec.setToolTip("按住測試 PTT 收音")
        self.btn_test_rec.setFixedWidth(85) # v2.9.1: Wider for label visibility
        self.btn_test_rec.setFixedHeight(32)
        self.btn_test_rec.setStyleSheet("background: #444; border-radius: 4px; font-size: 13px; font-weight: bold;")
        self.btn_test_rec.pressed.connect(self.test_start.emit)
        self.btn_test_rec.released.connect(self.test_stop.emit)
        
        lbl_ptt = QLabel("錄音按住 (PTT)")
        lbl_ptt.setFixedWidth(120) 
        row_ptt.addWidget(lbl_ptt)
        row_ptt.addWidget(self.btn_ptt)
        row_ptt.addWidget(self.btn_test_rec)
        row_ptt.addStretch(1) # Ensure alignment
        grid_layout.addLayout(row_ptt)

        # v2.8.15: Re-add LLM Hotkey
        row_llm = QHBoxLayout()
        self.btn_llm = HotkeyRecorderButton(self.config.get("hotkey_llm", "f14"))
        self.btn_llm.setFixedHeight(32)
        self.btn_llm.setFixedWidth(160)
        
        self.btn_test_llm = QPushButton("🚀 測試")
        self.btn_test_llm.setFixedWidth(85)
        self.btn_test_llm.setFixedHeight(32)
        self.btn_test_llm.setStyleSheet("background: #444; border-radius: 4px; font-size: 13px; font-weight: bold;")
        self.btn_test_llm.clicked.connect(self.test_llm.emit)

        lbl_llm = QLabel("潤飾模式 (LLM)")
        lbl_llm.setFixedWidth(120)
        row_llm.addWidget(lbl_llm)
        row_llm.addWidget(self.btn_llm)
        row_llm.addWidget(self.btn_test_llm)
        row_llm.addStretch(1)
        grid_layout.addLayout(row_llm)
        
        row_toggle = QHBoxLayout()
        self.btn_toggle = HotkeyRecorderButton(self.config.get("hotkey_toggle", "f13"))
        self.btn_toggle.setFixedHeight(32)
        self.btn_toggle.setFixedWidth(160)
        
        self.btn_test_toggle = QPushButton("🚀 測試")
        self.btn_test_toggle.setToolTip("點按測試 Toggle 收音")
        self.btn_test_toggle.setFixedWidth(85) # v2.9.1: Wider
        self.btn_test_toggle.setFixedHeight(32)
        self.btn_test_toggle.setStyleSheet("background: #444; border-radius: 4px; font-size: 13px; font-weight: bold;")
        self.btn_test_toggle.clicked.connect(self.test_toggle.emit)

        lbl_toggle = QLabel("錄音開關 (Toggle)")
        lbl_toggle.setFixedWidth(120) 
        row_toggle.addWidget(lbl_toggle)
        row_toggle.addWidget(self.btn_toggle)
        row_toggle.addWidget(self.btn_test_toggle)
        row_toggle.addStretch(1)
        grid_layout.addLayout(row_toggle)
        
        layout.addWidget(hotkey_grid)
        
        layout.addWidget(self._page_section_header("⚙️ 偏好設定"))
        self.auto_paste = QCheckBox("結果自動貼上 (Paste automatically)")
        self.auto_paste.setChecked(self.config.get("auto_paste", True))
        layout.addWidget(self.auto_paste)

        self.show_floating_button = QCheckBox("顯示顯示浮動按鈕 (Show Floating Button)")
        self.show_floating_button.setChecked(self.config.get("show_floating_button", True))
        layout.addWidget(self.show_floating_button)
        
        self.completion_sound = QCheckBox("錄音完成時播放音效 (Play sound on completion)")
        self.completion_sound.setChecked(self.config.get("completion_sound", True))
        layout.addWidget(self.completion_sound)

        self.debug_mode = QCheckBox("啟用詳細日誌輸出 (Debug logging)")
        self.debug_mode.setChecked(self.config.get("debug_mode", False))
        layout.addWidget(self.debug_mode)
       
        self.separate_keystrike_log = QCheckBox("獨立記錄熱鍵事件 (Separate KeyStrike Log to keystrike.log)")
        self.separate_keystrike_log.setChecked(self.config.get("separate_keystrike_log", False))
        layout.addWidget(self.separate_keystrike_log) 
        
        self.debug_demo_mode = QCheckBox("情境模擬 Demo 版 (需API KEY連結雲端LLM) (Debug Scenario Demo Mode)") #咖啡版功能
        self.debug_demo_mode.setChecked(self.config.get("is_demo", False)) #咖啡版功能
        layout.addWidget(self.debug_demo_mode) #咖啡版功能

        self.output_prefix = QCheckBox("顯示模式名稱前綴 (需API KEY連結雲端LLM)  (Output with Mode Prefix)") #咖啡版功能
        self.output_prefix.setChecked(self.config.get("output_prefix", False)) #咖啡版功能
        layout.addWidget(self.output_prefix) #咖啡版功能

        self.showcase_mode = QCheckBox("LLM 展示版 (需API KEY連結雲端LLM)  (LLM Showcase Mode: [STT] + [LLM])") #咖啡版功能
        self.showcase_mode.setChecked(self.config.get("showcase_mode", False)) #咖啡版功能
        layout.addWidget(self.showcase_mode) #咖啡版功能

        layout.addWidget(self._page_section_header("🛠️ 診斷與修復"))
        
        diag_grid = QGridLayout()
        diag_grid.setContentsMargins(0, 5, 0, 5)
        diag_grid.setSpacing(10)

        self.btn_mic_test = QPushButton("🎤 麥克風測試與診斷 (Mic Test)")
        self.btn_mic_test.setObjectName("secondary")
        self.btn_mic_test.clicked.connect(self._run_mic_test)
        diag_grid.addWidget(self.btn_mic_test, 0, 0)
        
        self.btn_run_self_check = QPushButton("🔍 系統自我檢測 (Self-Check)")
        self.btn_run_self_check.setObjectName("secondary")
        self.btn_run_self_check.clicked.connect(self._run_self_check)
        diag_grid.addWidget(self.btn_run_self_check, 0, 1)

        if platform.system() == "Windows":
            self.btn_mic_test.hide()
            self.btn_run_self_check.hide()

        self.btn_view_logs = QPushButton("📄 檢視詳細日誌 (View Detail Logs)")
        self.btn_view_logs.setObjectName("secondary")
        self.btn_view_logs.clicked.connect(self._view_debug_log)
        diag_grid.addWidget(self.btn_view_logs, 1, 0)

        self.btn_view_keystrike = QPushButton("📄 檢視熱鍵紀錄 (View Keys Logs)")
        self.btn_view_keystrike.setObjectName("secondary")
        self.btn_view_keystrike.clicked.connect(self._view_keystrike_log)
        diag_grid.addWidget(self.btn_view_keystrike, 1, 1)

        self.btn_open_folder = QPushButton("📂 開啟數據與模型目錄 (Open Data/Models)")
        self.btn_open_folder.setObjectName("secondary")
        self.btn_open_folder.clicked.connect(self._open_data_folder)
        diag_grid.addWidget(self.btn_open_folder, 2, 0, 1, 2) # Span 2 columns

        layout.addLayout(diag_grid)
        
        layout.addStretch()
        return page
    # ── 同步邏輯 (Sync Logic) ────────────────────────────────────
    def _set_sync_directory(self):
        """選擇同步目錄並引導遷移資料。"""
        dir_path = QFileDialog.getExistingDirectory(self, "選擇 NAS 或雲端同步資料夾")
        if not dir_path:
            return

        from paths import SYNC_POINTER_PATH, APP_DATA_DIR
        
        # 1. 存入指標
        try:
            SYNC_POINTER_PATH.write_text(dir_path, encoding="utf-8")
        except Exception as e:
            QMessageBox.critical(self, "失敗", f"無法寫入同步指針：{e}")
            return

        # 2. 詢問是否遷移資料
        reply = QMessageBox.question(
            self, "資料遷移",
            "是否要將目前的靈魂情境、辭典與記憶「遷移」到新的同步目錄中？\n\n"
            "※ 如果該目錄已有資料，選『否』將直接連結現有資料。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._migrate_to_sync(Path(dir_path))
        
        QMessageBox.information(self, "成功", "同步路徑已設定完成！請重啟應用程式以生效。")
        self.sync_status_lbl.setText(f"✅ 已同步至：{dir_path}")
        self.sync_status_lbl.setStyleSheet("color: #00e676; font-weight: bold;")

    def _migrate_to_sync(self, target_base: Path):
        """將本地資料搬移至同步目錄。"""
        from paths import APP_DATA_DIR
        folders_to_sync = ["soul", "vocab", "memory", "stats"]
        files_to_sync = ["ai_permanent_memory.md"]

        for folder in folders_to_sync:
            src = APP_DATA_DIR / folder
            dst = target_base / folder
            if src.exists():
                try:
                    if dst.exists(): shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                except Exception as e:
                    print(f"[Sync] Error migrating folder {folder}: {e}")

        for filename in files_to_sync:
            src = APP_DATA_DIR / filename
            dst = target_base / filename
            if src.exists():
                try:
                    shutil.copy2(src, dst)
                except Exception as e:
                    print(f"[Sync] Error migrating file {filename}: {e}")

    def _clear_sync_directory(self):
        """取消同步。"""
        from paths import SYNC_POINTER_PATH
        if SYNC_POINTER_PATH.exists():
            SYNC_POINTER_PATH.unlink()
            QMessageBox.information(self, "重設", "已取消同步，改回使用本地存儲。請重啟程式。")
            self.sync_status_lbl.setText("目前狀態：本地存儲 (Local Only)")
            self.sync_status_lbl.setStyleSheet("color: #aaa; font-weight: bold;")


    def _page_section_header(self, text):
        l = QLabel(text)
        l.setStyleSheet("font-weight: bold; font-size: 16px; color: #7c4dff; margin-top: 10px; margin-bottom: 5px;")
        return l

    def _add_grid_row(self, layout, label_text, widget):
        row = QHBoxLayout()
        l = QLabel(label_text)
        l.setFixedWidth(160)
        row.addWidget(l)
        row.addWidget(widget)
        layout.addLayout(row)
        return widget

    # --- Data and Logic ---
    def _load_data(self):
        if SOUL_BASE_PATH.exists():
            raw_bytes = SOUL_BASE_PATH.read_bytes()
            content = ""
            for enc in ["utf-8-sig", "utf-8", "big5", "utf-16", "gbk"]:
                try:
                    content = raw_bytes.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            if not content:
                # Fallback directly to replace if all fail
                content = raw_bytes.decode("utf-8", errors="replace")
            self.soul_prompt.setPlainText(content)
        
        # 1. 語音辨識
        stt_val = self.config.get("stt_engine", "local_whisper")
        stt_idx = self.stt_engine.findData(stt_val)
        if stt_idx >= 0: self.stt_engine.setCurrentIndex(stt_idx)
        else: self.stt_engine.setCurrentText(stt_val)
            
        m_val = self.config.get("whisper_model", "medium")
        m_idx = self.whisper_model.findData(m_val)
        if m_idx >= 0: self.whisper_model.setCurrentIndex(m_idx)
        else: self.whisper_model.setCurrentText(m_val)
        
        self.groq_key.setText(self.config.get("groq_api_key", ""))
        
        # 2. 語言與 AI 配置
        lang_val = self.config.get("language", "zh")
        lang_idx = self.language.findData(lang_val)
        if lang_idx >= 0: self.language.setCurrentIndex(lang_idx)
        else: self.language.setCurrentText(lang_val)
        
        self.llm_enabled.setChecked(self.config.get("llm_enabled", False))
        self.llm_engine.setCurrentText(self.config.get("llm_engine", "ollama"))
        self.llm_mode.setCurrentText(self.config.get("llm_mode", "replace"))
        
        # API Keys
        self.openai_key.setText(self.config.get("openai_api_key", ""))
        self.anthropic_key.setText(self.config.get("anthropic_api_key", ""))
        self.gemini_key.setText(self.config.get("gemini_api_key", ""))
        self.openrouter_key.setText(self.config.get("openrouter_api_key", ""))
        self.qwen_key.setText(self.config.get("qwen_api_key", ""))
        self.deepseek_key.setText(self.config.get("deepseek_api_key", ""))
        
        self.magic_trigger.setText(self.config.get("magic_trigger", "嘿 VoiceType"))
        
        # 3. 系統設定 (Critical: fix UI overwriting disk with stale state)
        self.btn_ptt.key_str = self.config.get("hotkey_ptt", "alt_r")
        self.btn_toggle.key_str = self.config.get("hotkey_toggle", "f13")
        self.btn_llm.key_str = self.config.get("hotkey_llm", "f14")
        
        self.auto_paste.setChecked(self.config.get("auto_paste", True))
        self.show_floating_button.setChecked(self.config.get("show_floating_button", True))
        self.completion_sound.setChecked(self.config.get("completion_sound", True))
        self.debug_mode.setChecked(self.config.get("debug_mode", False))
        self.debug_demo_mode.setChecked(self.config.get("is_demo", False))
        self.output_prefix.setChecked(self.config.get("output_prefix", False))
        self.separate_keystrike_log.setChecked(self.config.get("separate_keystrike_log", False))
        self.showcase_mode.setChecked(self.config.get("showcase_mode", False))
        self.memory_inject_cb.setChecked(self.config.get("memory_enabled", False))

        # Refreshes
        self._refresh_vocab()
        self._refresh_learned_vocab()
        self._refresh_memory()
        self._refresh_stats()
        self._update_dashboard_status()

    def refresh_config(self, new_config):
        """外部呼叫：強制重載設定到 UI (防止 stale data)"""
        self.config = new_config.copy()
        self._load_data()

    def _update_dashboard_status(self):
        ai = "已開啟" if self.config.get("llm_enabled") else "已關閉"
        self.lbl_status_ai.setText(f"AI 潤飾: {ai}")
        self.lbl_status_ai.setStyleSheet(f"color: {'#7c4dff' if ai == '已開啟' else '#666'}; font-weight: bold; font-size: 16px;")
        
        eng = self.config.get("stt_engine", "local_whisper")
        self.lbl_status_stt.setText(f"引擎: {eng.upper()}")
        
        # 檢查權限與模型狀態
        self._check_all_permissions()
        self._check_local_models()

    def update_download_progress(self, status: str, value: int = -1, done: bool = False):
        """由 main.py 呼叫，更新模型下載進度卡片。"""
        try:
            if done:
                self.download_card.setVisible(False)
                self._check_local_models()  # 刷新模型綠燈
            else:
                self.download_card.setVisible(True)
                self.lbl_download_status.setText(status)
                if value >= 0:
                    self.download_progress.setRange(0, 100)
                    self.download_progress.setValue(value)
                else:
                    self.download_progress.setRange(0, 0) # Indeterminate
        except Exception:
            pass

    def _check_all_permissions(self):
        import logging
        log = logging.getLogger("voicetype")
        
        # Windows 不需要 macOS TCC 權限檢查，全部亮綠燈
        if platform.system() == "Windows":
            self.light_acc.set_status(True)
            self.light_input.set_status(True)
            self.light_mic.set_status(True)
            log.info("[PERM] Windows: All permissions auto-granted.")
            return

        log.info("[PERM] Windows: All permissions auto-granted.")

    def _check_local_models(self):
        """檢查 Faster-Whisper 模型是否已下載到本機快取"""
        self.light_model_small.set_status(self._is_model_present("small"))
        self.light_model_medium.set_status(self._is_model_present("medium"))
        self.light_model_large.set_status(self._is_model_present("large"))

    def _is_model_present(self, size: str) -> bool:
        try:
            cache_path = Path.home() / ".cache" / "huggingface" / "hub"
            if not cache_path.exists():
                return False
            
            # faster-whisper: models--Systran--faster-whisper-<size>
            prefixes = [
                f"models--Systran--faster-whisper-{size}",
            ]
            
            for p in cache_path.iterdir():
                if p.is_dir() and any(p.name.startswith(pref) for pref in prefixes):
                    # 檢查是否有 snapshot
                    snap = p / "snapshots"
                    if snap.exists() and any(snap.iterdir()):
                        return True
            return False
        except Exception:
            return False

    def _populate_whisper_models(self):
        """依據模型大小、本機狀態與推薦程度，格式化顯示 COMBOBOX 選單內容"""
        self.whisper_model.clear()
        meta = {
            "tiny":   ("75MB",  "極速辨識"),
            "base":   ("145MB", "快速辨識"),
            "small":  ("500MB", "輕量，速度快"),
            "medium": ("1.5GB", "均衡型，推薦首選"),
            "large":  ("3.0GB", "極限型，最精準"),
        }
        # 依序加入 Tiny 到 Large
        for m in ["tiny", "base", "small", "medium", "large"]:
            if m in meta:
                size, desc = meta[m]
                is_ready = self._is_model_present(m)
                status = " (已就緒)" if is_ready else " (未下載)"
                label = f"{m.upper():<8} [{size}] - {desc}{status}"
                self.whisper_model.addItem(label, m) # m 為內部代號，例如 "medium"

    def _refresh_vocab(self):
        self.vocab_list.clear()
        try:
            from vocab.manager import load_custom_vocab
            for word in load_custom_vocab():
                self.vocab_list.addItem(word)
        except: pass

    def _refresh_learned_vocab(self):
        self.learned_list.clear()
        self.dashboard_vocab.clear()
        try:
            from vocab.manager import load_all_learned_words, load_auto_memory
            memory = load_auto_memory()
            words = load_all_learned_words()
            for word in words:
                count = memory.get(word, 0)
                self.learned_list.addItem(f"{word} ({count})")
            # Dashboard only show top 5
            for word in words[:5]:
                self.dashboard_vocab.addItem(word)
        except: pass

    def _promote_vocab(self):
        item = self.learned_list.currentItem()
        if not item: return
        word = item.text().split(" (")[0]
        try:
            from vocab.manager import promote_learned_word
            promote_learned_word(word)
            self._refresh_vocab()
            self._refresh_learned_vocab()
        except Exception as e:
            QMessageBox.critical(self, "錯誤", str(e))

    def _delete_learned_word(self):
        item = self.learned_list.currentItem()
        if not item: return
        word = item.text().split(" (")[0]
        try:
            from vocab.manager import remove_learned_word
            remove_learned_word(word)
            self._refresh_learned_vocab()
        except Exception as e:
            QMessageBox.critical(self, "錯誤", str(e))

    def _refresh_memory(self):
        self.mem_tree.clear()
        try:
            from memory.manager import load_memory
            memory = load_memory()
            summary = memory.get("summary", "")
            if summary:
                self.mem_tree.addTopLevelItem(QTreeWidgetItem(["[摘要]", summary[:60] + "..."]))
            for entry in reversed(memory.get("entries", [])):
                ts = entry.get("ts", "")[:16]
                text = (entry.get("llm") or entry.get("stt", ""))[:40]
                self.mem_tree.addTopLevelItem(QTreeWidgetItem([ts, text + "..."]))
        except: pass

    def _purge_memory(self):
        from memory.manager import load_memory
        count = len(load_memory().get("entries", []))
        if count == 0:
            QMessageBox.information(self, "記憶壓縮", "目前沒有可壓縮的記憶條目。")
            return
        reply = QMessageBox.question(
            self, "確認壓縮記憶",
            f"將 {count} 筆原始記錄壓縮為摘要，原始資料將歸檔保留。確定？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            from memory.manager import purge_and_summarize
            purged = purge_and_summarize()
            self._refresh_memory()
            QMessageBox.information(self, "壓縮完成", f"已壓縮 {purged} 筆記錄，摘要已更新。")
        except Exception as e:
            QMessageBox.critical(self, "錯誤", str(e))

    def _refresh_stats(self):
        self.stats_tree.clear()
        try:
            from stats.tracker import get_summary
            s = get_summary()
            self.lbl_today_count.setText(f"{s['today']['sessions']} 次錄音")
            self.lbl_today_chars.setText(f"錄製約 {s['today']['chars']} 字")
            
            # 計算省下時間 (以一般人打字速度 40字/分 計算)
            total_chars = s['total']['chars']
            saved_mins = total_chars / 40.0
            if saved_mins < 60:
                self.lbl_time_saved.setText(f"{saved_mins:.1f} 分鐘")
            else:
                self.lbl_time_saved.setText(f"{saved_mins/60.0:.1f} 小時")
            self.lbl_total_chars_desc.setText(f"累計辨識 {total_chars} 字")
            
            def format_saved(chars):
                mins = chars / 40.0
                if mins < 60: return f"{mins:.1f}m"
                return f"{mins/60.0:.1f}h"

            self.stats_tree.addTopLevelItem(QTreeWidgetItem([
                "今日", str(s["today"]["sessions"]), f"{s['today']['duration']}s", str(s["today"]["chars"]), format_saved(s["today"]["chars"])
            ]))
            self.stats_tree.addTopLevelItem(QTreeWidgetItem([
                "本週", str(s["week"]["sessions"]), f"{s['week']['duration']}s", str(s["week"]["chars"]), format_saved(s["week"]["chars"])
            ]))
            self.stats_tree.addTopLevelItem(QTreeWidgetItem([
                "累積", str(s["total"]["sessions"]), f"{s['total']['duration']}s", str(s["total"]["chars"]), format_saved(s["total"]["chars"])
            ]))
        except: pass

    def _add_vocab(self):
        word = self.vocab_input.text().strip()
        if not word: return
        from vocab.manager import add_custom_word
        add_custom_word(word)
        self.vocab_input.clear()
        self._refresh_vocab()

    def _del_vocab(self):
        item = self.vocab_list.currentItem()
        if not item: return
        from vocab.manager import remove_custom_word
        remove_custom_word(item.text())
        self._refresh_vocab()

    def _save_action(self):
        self.config["stt_engine"] = self.stt_engine.currentData() or self.stt_engine.currentText()
        # 使用 currentData 取得內部代號如 "medium" 而非顯示文字
        self.config["whisper_model"] = self.whisper_model.currentData() or self.whisper_model.currentText()
        self.config["groq_api_key"] = self.groq_key.text().strip()
        self.config["language"] = self.language.currentData() or self.language.currentText()
        self.config["llm_enabled"] = self.llm_enabled.isChecked()
        self.config["llm_engine"] = self.llm_engine.currentText()
        self.config["llm_mode"] = self.llm_mode.currentText()
        self.config["openai_api_key"] = self.openai_key.text().strip()
        self.config["anthropic_api_key"] = self.anthropic_key.text().strip()
        self.config["gemini_api_key"] = self.gemini_key.text().strip()
        self.config["openrouter_api_key"] = self.openrouter_key.text().strip()
        self.config["qwen_api_key"] = self.qwen_key.text().strip()
        self.config["deepseek_api_key"] = self.deepseek_key.text().strip()
        self.config["magic_trigger"] = self.magic_trigger.text().strip() or "嘿 VoiceType"
        self.config["hotkey_ptt"] = self.btn_ptt.key_str
        self.config["hotkey_toggle"] = self.btn_toggle.key_str
        self.config["hotkey_llm"] = self.btn_llm.key_str
        
        log.info(f"[save] Writing UI hotkeys to config: PTT={self.config['hotkey_ptt']}, Toggle={self.config['hotkey_toggle']}, LLM={self.config['hotkey_llm']}")
        self.config["auto_paste"] = self.auto_paste.isChecked()
        self.config["completion_sound"] = self.completion_sound.isChecked()
        self.config["debug_mode"] = self.debug_mode.isChecked()
        self.config["is_demo"] = self.debug_demo_mode.isChecked() # Match key used in main.py
        self.config["output_prefix"] = self.output_prefix.isChecked()
        self.config["separate_keystrike_log"] = self.separate_keystrike_log.isChecked()
        self.config["show_floating_button"] = self.show_floating_button.isChecked()
        self.config["showcase_mode"] = self.showcase_mode.isChecked()
        self.config["memory_enabled"] = self.memory_inject_cb.isChecked()

        try:
            SOUL_BASE_PATH.write_text(self.soul_prompt.toPlainText().strip(), encoding="utf-8")
        except: pass

        save_config(self.config)
        # v2.7.32: Windows 穩定性優先，提示手動重啟而非自動連鎖反應
        QMessageBox.information(self, "嘴炮輸入法", "設定已儲存！\n\n為了確保「啟動防護」與「載入模組」完整生效，請務必手動『結束並重啟』本程式。")
        if self.on_save: self.on_save(self.config)
        self.close()

    def _run_self_check(self):
        import subprocess
        import sys
        import os
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "self_check.py")
        if os.path.exists(script_path):
            # Launch in a new terminal window on Windows
            if platform.system() == "Windows":
                subprocess.Popen(["cmd.exe", "/c", "start", sys.executable, script_path])
            else:
                subprocess.Popen([sys.executable, script_path])
        else:
            QMessageBox.warning(self, "錯誤", f"找不到檢測程式：{script_path}")

    def _view_debug_log(self):
        from paths import APP_DATA_DIR
        log_path = APP_DATA_DIR / "debug.log"
        if log_path.exists():
            import os, platform
            if platform.system() == "Windows":
                os.startfile(str(log_path))
            else:
                import subprocess
                subprocess.run(["open", str(log_path)])
        else:
            QMessageBox.information(self, "資訊", f"日誌檔案尚未建立：\n{log_path}")

    def _view_keystrike_log(self):
        from paths import KEYSTRIKE_LOG_PATH
        if KEYSTRIKE_LOG_PATH.exists():
            import os, platform
            if platform.system() == "Windows":
                os.startfile(str(KEYSTRIKE_LOG_PATH))
            else:
                import subprocess
                subprocess.run(["open", str(KEYSTRIKE_LOG_PATH)])
        else:
            QMessageBox.information(self, "資訊", f"熱鍵日誌檔案尚未建立：\n{KEYSTRIKE_LOG_PATH}")

    def _open_data_folder(self):
        from paths import APP_DATA_DIR
        if APP_DATA_DIR.exists():
            import os, platform
            if platform.system() == "Windows":
                os.startfile(str(APP_DATA_DIR))
            else:
                import subprocess
                subprocess.run(["open", str(APP_DATA_DIR)])
        else:
            QMessageBox.information(self, "資訊", f"數據目錄尚未建立：\n{APP_DATA_DIR}")

    def run(self):
        self.show()

    def _run_mic_test(self):
        from PyQt6.QtWidgets import QMessageBox, QProgressDialog
        import sounddevice as sd
        import numpy as np
        import platform
        import time

        if platform.system() != "Darwin":
            QMessageBox.information(self, "系統診斷", "此診斷功能目前專為 macOS 設計。")
            return

        reply = QMessageBox.question(self, "麥克風測試", 
                                   "即將開始 3 秒鐘的錄音測試，請對著麥克風說話。\n\n準備好了嗎？",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.No:
            return

        # Create a non-modal (but blocking) progress dialog
        progress = QProgressDialog("正在錄音中，請說話...", None, 0, 3, self)
        progress.setWindowTitle("麥克風測試")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()
        
        fs = 16000
        duration = 3.0
        
        try:
            recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='float32')
            
            for i in range(3):
                progress.setValue(i)
                QApplication.processEvents()
                time.sleep(1)
            
            sd.wait()
            progress.setValue(3)
            progress.close()
            
            energy = np.sqrt(np.mean(recording**2))
            
            if energy < 1e-7:
                QMessageBox.critical(self, "測試失敗",
                    "偵測到【完全靜音】(Silence)。\n\n請至 Windows 設定 → 隱私權 → 麥克風，確認已授權本程式存取麥克風。")
            elif energy < 1e-3:
                QMessageBox.warning(self, "測試警告", 
                    f"音訊能源過低 ({energy:.6f})。\n\n請檢查系統輸入音量設定。")
            else:
                QMessageBox.information(self, "測試成功", 
                    f"成功接收音訊資料！\n能源強度: {energy:.6f}\n您的麥克風運作正常。")
                
        except Exception as e:
            if 'progress' in locals(): progress.close()
            QMessageBox.critical(self, "錯誤", f"錄音測試失敗: {str(e)}")

def has_api_key(config: dict) -> bool:
    stt = config.get("stt_engine", "local_whisper")
    if stt == "local_whisper" and (not config.get("llm_enabled") or config.get("llm_engine") == "ollama"):
        return True
    for k in ["groq_api_key", "openai_api_key", "openrouter_api_key"]:
        if config.get(k): return True
    return False


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = SettingsWindow()
    win.show()
    sys.exit(app.exec())
