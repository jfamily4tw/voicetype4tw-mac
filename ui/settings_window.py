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
    QMessageBox, QFileDialog, QScrollArea, QFrame, QSplitter, QSizePolicy, QSlider
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QRect, QUrl, QTimer
from PyQt6.QtGui import QFont, QIcon, QColor, QPainter, QLinearGradient, QBrush, QPixmap, QDesktopServices
import shutil

import logging
from config import load_config, save_config
from paths import SOUL_BASE_PATH, SOUL_SCENARIO_DIR, SOUL_FORMAT_DIR, SOUL_TEMPLATE_DIR, BUILD_ID
from ui.skin_manager import SkinManager, AVAILABLE_SKINS

log = logging.getLogger("voicetype.ui")
STT_ENGINES = ["mlx_whisper", "groq", "gemini", "openrouter"]
LLM_ENGINES = ["ollama", "openai", "claude", "openrouter", "gemini", "deepseek", "qwen"]
WHISPER_MODELS = ["tiny", "base", "small", "medium", "large"]
TRIGGER_MODES = ["push_to_talk", "toggle"]
HOTKEYS = ["right_option", "left_option", "right_ctrl", "f13", "f14", "f15"]
LLM_MODES = ["replace", "fast"]

from hotkey.listener import key_to_str, str_to_key

# ── Material Symbols font loader ─────────────────────────────
_MS_FONT_LOADED = False
_MS_FONT_FAMILY = "Material Symbols Outlined"

# Direct Unicode codepoints (no ligature needed)
_MS_CODEPOINTS = {
    "auto_awesome": "\ue65f", "balance": "\ueaf6", "bar_chart": "\ue26b",
    "bolt": "\uea0b", "build": "\uf8cd", "cloud_sync": "\ueb5a",
    "health_and_safety": "\ue1d5", "history": "\ue8b3", "home": "\ue9b2",
    "keyboard": "\ue312", "lock_open": "\ue898", "manage_accounts": "\uf02e",
    "menu_book": "\uea19", "mic": "\ue31d", "mic_external_on": "\uef5a",
    "psychology": "\uea4a", "settings": "\ue8b8", "shield": "\ue9e0",
    "refresh": "\ue5d5", "smart_toy": "\uf06c", "terminal": "\ueb8e", "tune": "\ue429",
    "visibility": "\ue8f4",
}

def _load_ms_font():
    global _MS_FONT_LOADED, _MS_FONT_FAMILY
    if _MS_FONT_LOADED:
        return
    from PyQt6.QtGui import QFontDatabase
    import os
    # py2app bundle: RESOURCEPATH = Contents/Resources/
    # dev: fall back to __file__-relative path
    res_path = os.environ.get("RESOURCEPATH")
    if res_path:
        font_path = os.path.join(res_path, "assets", "fonts", "MaterialSymbolsOutlined.ttf")
    else:
        font_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                  "assets", "fonts", "MaterialSymbolsOutlined.ttf")
    if os.path.exists(font_path):
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id >= 0:
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families:
                _MS_FONT_FAMILY = families[0]
    _MS_FONT_LOADED = True

def _ms_char(name: str) -> str:
    """Return the Unicode character for the given Material Symbol name."""
    return _MS_CODEPOINTS.get(name, name)

def ms_icon(name: str, size: int = 18, color: str = "") -> QLabel:
    """Return a QLabel that renders a Material Symbol icon via codepoint."""
    _load_ms_font()
    lbl = QLabel(_ms_char(name))
    # Must include font-family in stylesheet to override global QSS (which sets PingFang TC on all QLabel)
    color_rule = f"color: {color};" if color else ""
    lbl.setStyleSheet(
        f"background: transparent; border: none; font-family: '{_MS_FONT_FAMILY}'; font-size: {size}pt; {color_rule}"
    )
    lbl.setFixedSize(size + 8, size + 8)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return lbl

def ms_icon_pixmap(name: str, size: int = 22, color: str = "#e4e1e6"):
    """Render a Material Symbol to a HiDPI-aware QPixmap for use as QIcon."""
    from PyQt6.QtGui import QPixmap, QPainter, QFont, QColor
    _load_ms_font()
    dpr = 3  # HiDPI: render at 3× for Retina
    px_size = size * dpr
    px = QPixmap(px_size, px_size)
    px.setDevicePixelRatio(dpr)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QColor(color))
    font = QFont(_MS_FONT_FAMILY)
    font.setPixelSize(size - 2)  # logical pixel size (painter uses logical coords when DPR is set)
    p.setFont(font)
    from PyQt6.QtCore import QRect
    p.drawText(QRect(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, _ms_char(name))
    p.end()
    return px


class GlassCard(QFrame):
    """A premium looking card with subtle border and background.
    Styling is controlled by global QSS via SkinManager (targets GlassCard class name)."""
    def __init__(self, parent=None):
        super().__init__(parent)

class SidebarButton(QPushButton):
    def __init__(self, icon_name, label, index, on_click, parent=None):
        super().__init__(parent)
        self.index = index
        self.setCheckable(True)
        import platform
        font_family = "Taipei Sans TC Beta" if platform.system() == "Darwin" else "Microsoft JhengHei"
        self.setText(f"  {label}")
        self.setFont(QFont(font_family, 16, QFont.Weight.Medium))
        # Set Material Symbol as icon
        from PyQt6.QtGui import QIcon
        s = SkinManager.current()
        px = ms_icon_pixmap(icon_name, 22, s.get("text_secondary", "#A1A1AA"))
        self.setIcon(QIcon(px))
        self.setIconSize(QSize(22, 22))
        self.setFixedHeight(60)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(lambda: on_click(self.index))
        # Styling via global QSS (SkinManager targets SidebarButton class name)

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

def translate_key_string(key_str):
    import re
    if not key_str:
        return "未設定"
    
    match = re.search(r'\(?code:(\d+)\)?', key_str, re.IGNORECASE)
    if not match:
        return key_str # fallback to literal if no code is present
        
    code = int(match.group(1))
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


class ToggleSwitch(QWidget):
    """iOS 風格的開關元件，替代 QCheckBox 讓狀態更清晰可見。"""
    toggled = pyqtSignal(bool)

    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self._checked = checked
        self.setFixedSize(48, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, val: bool):
        self._checked = val
        self.update()

    def mousePressEvent(self, event):
        self._checked = not self._checked
        self.toggled.emit(self._checked)
        self.update()

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter, QColor, QPen
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s = SkinManager.current()
        if self._checked:
            track_color = QColor(s['accent'])
        else:
            track_color = QColor(s['bg_input_border'])
        # Track
        p.setBrush(track_color)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 3, 48, 20, 10, 10)
        # Knob
        knob_x = 26 if self._checked else 2
        knob_color = QColor(s['bg_window']) if self._checked else QColor(s['text_secondary'])
        p.setBrush(knob_color)
        p.drawEllipse(knob_x, 5, 18, 16)
        p.end()


class StatusChip(QFrame):
    """Titanium 風格的狀態晶片：圖示 + 標籤 + 狀態文字，實現 set_status() 介面。"""
    def __init__(self, icon: str, label: str, preference_url: str = "", parent=None):
        super().__init__(parent)
        self.url = preference_url
        s = SkinManager.current()

        self.setStyleSheet(f"""
            StatusChip {{
                background-color: {s['bg_card']};
                border: 1px solid {s['card_border']};
                border-radius: 10px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_icon = ms_icon(icon, size=22, color=s['text_primary'])
        self.lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_icon, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.lbl_label = QLabel(label.upper())
        self.lbl_label.setStyleSheet(f"font-size: 9px; font-weight: bold; letter-spacing: 1px; color: {s['text_secondary']}; background: transparent; border: none;")
        self.lbl_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.lbl_status = QLabel("—")
        self.lbl_status.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {s['text_primary']}; background: transparent; border: none;")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_status, alignment=Qt.AlignmentFlag.AlignHCenter)

        if preference_url:
            self.fix_btn = QPushButton("修復")
            self.fix_btn.setFixedHeight(22)
            self.fix_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: 1px solid {s['text_secondary']};
                    color: {s['text_secondary']};
                    border-radius: 4px;
                    font-size: 10px;
                    padding: 2px 8px;
                }}
                QPushButton:hover {{ color: {s['text_primary']}; border-color: {s['text_primary']}; }}
            """)
            self.fix_btn.hide()
            self.fix_btn.clicked.connect(self._open_preference)
            layout.addWidget(self.fix_btn)
        else:
            self.fix_btn = None

    def _open_preference(self):
        import subprocess
        subprocess.run(["open", self.url])

    def set_status(self, authorized: bool):
        s = SkinManager.current()
        ok_color = s['success']
        fail_color = s['danger']
        if authorized:
            self.lbl_status.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {ok_color}; background: transparent; border: none;")
            self.lbl_status.setText("已授權")
        else:
            self.lbl_status.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {fail_color}; background: transparent; border: none;")
            self.lbl_status.setText("未授權")
        if self.fix_btn:
            self.fix_btn.setVisible(not authorized)


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
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        top_layout = QHBoxLayout()
        top_layout.setSpacing(6)
        self.dot = QFrame()
        self.dot.setFixedSize(10, 10)
        self.dot.setStyleSheet("background-color: #555; border-radius: 5px;")
        top_layout.addWidget(self.dot, alignment=Qt.AlignmentFlag.AlignVCenter)

        self.label = QLabel(f"{model_name} ({size_info})")
        win_font = "Microsoft JhengHei" if platform.system() == "Windows" else ""
        self.label.setStyleSheet(f"color: #e2e4e7; font-size: 13px; font-weight: bold; font-family: '{win_font}';")
        top_layout.addWidget(self.label)
        layout.addLayout(top_layout, stretch=0)
        layout.setAlignment(top_layout, Qt.AlignmentFlag.AlignHCenter)

        self.desc = QLabel(desc_text)
        win_font = "Microsoft JhengHei" if platform.system() == "Windows" else ""
        self.desc.setStyleSheet(f"color: #888; font-size: 11px; font-family: '{win_font}';")
        self.desc.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.desc, alignment=Qt.AlignmentFlag.AlignHCenter)

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
        self._is_dark = True

        # 載入 skin
        skin_name = self.config.get("ui_skin", "titanium")
        self.skin = SkinManager.load(skin_name)

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
        
        # 全域 QSS 由 SkinManager 生成
        font_family = "PingFang TC"
        self.setStyleSheet(SkinManager.build_qss(font_family))

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        sidebar_container = QWidget()
        sidebar_container.setObjectName("sidebar_container")
        sidebar_container.setFixedWidth(self.skin.get("sidebar_width", 256))
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
        
        os_ver = "Mac version" if platform.system() == "Darwin" else "Windows version"
        lbl_os = QLabel(os_ver)
        lbl_os.setStyleSheet("font-family: 'Myriad Pro'; font-style: italic; font-size: 14px; color: #8a8d91;")
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
            ("home",       "Dashboard"),
            ("mic",        "辨識 & AI"),
            ("auto_awesome","靈魂設定"),
            ("menu_book",  "詞彙 & 記憶"),
            ("cloud_sync", "雲端同步"),
            ("bar_chart",  "數據統計"),
            ("settings",   "系統設定"),
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
        credit_box = QLabel(f"{VERSION_NAME} | {BUILD_ID}\n主要開發者：吉米丘, CC58TW\n協助開發者：Gemini, Nebula")
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
        footer.setSpacing(12)
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
        s = self.skin
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        # ── Header ────────────────────────────────────────────
        hdr_row = QHBoxLayout()
        hdr_left = QVBoxLayout()
        hdr_left.setSpacing(3)
        lbl_title = QLabel("雲端同步 & NAS")
        lbl_title.setStyleSheet(f"font-size: 30px; font-weight: 800; color: {s['text_primary']}; letter-spacing: -1px; background: transparent;")
        lbl_sub = QLabel("Cross-Platform Sync — 在多台裝置間共用靈魂、詞彙與 AI 記憶。")
        lbl_sub.setStyleSheet(f"font-size: 12px; color: {s['text_secondary']}; background: transparent;")
        hdr_left.addWidget(lbl_title)
        hdr_left.addWidget(lbl_sub)
        hdr_row.addLayout(hdr_left)
        hdr_row.addStretch()
        layout.addLayout(hdr_row)

        # ── Two-column body ───────────────────────────────────
        body = QHBoxLayout()
        body.setSpacing(16)

        # ─ Left: 同步狀態 ─
        sync_card = GlassCard()
        sync_layout = QVBoxLayout(sync_card)
        sync_layout.setContentsMargins(24, 24, 24, 24)
        sync_layout.setSpacing(16)

        # Card header
        card_hdr = QHBoxLayout()
        card_title = QLabel("同步狀態")
        card_title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {s['text_primary']}; background: transparent;")
        card_sub = QLabel("Sync Configuration")
        card_sub.setStyleSheet(f"font-size: 11px; color: {s['text_secondary']}; background: transparent;")
        card_hdr_v = QVBoxLayout()
        card_hdr_v.setSpacing(2)
        card_hdr_v.addWidget(card_title)
        card_hdr_v.addWidget(card_sub)
        card_hdr.addLayout(card_hdr_v)
        card_hdr.addStretch()

        from paths import SYNC_POINTER_PATH
        is_synced = SYNC_POINTER_PATH.exists()
        dot_color = "#00e676" if is_synced else s['text_secondary']
        txt_color = s['text_primary'] if is_synced else s['text_secondary']
        status_badge = QLabel()
        status_badge.setTextFormat(Qt.TextFormat.RichText)
        status_badge.setText(
            f"<span style='color:{dot_color}'>●</span>"
            f"<span style='color:{txt_color}'> {'ACTIVE' if is_synced else 'LOCAL'}</span>"
        )
        status_badge.setStyleSheet(f"""
            background: {s['bg_input']};
            border: 1px solid {s['bg_input_border']};
            border-radius: 6px;
            font-size: 10px; font-weight: bold; padding: 3px 10px;
        """)
        card_hdr.addWidget(status_badge)
        sync_layout.addLayout(card_hdr)

        # Current path label
        lbl_path_label = QLabel("當前路徑")
        lbl_path_label.setStyleSheet(f"font-size: 11px; color: {s['text_secondary']}; background: transparent;")
        sync_layout.addWidget(lbl_path_label)

        self.sync_status_lbl = QLabel("本地存儲 (Local Only)")
        self.sync_status_lbl.setStyleSheet(f"""
            background: {s['bg_input']};
            border: 1px solid {s['bg_input_border']};
            border-radius: 8px;
            color: {s['text_primary']};
            padding: 10px 14px;
            font-size: 13px;
        """)
        self.sync_status_lbl.setWordWrap(True)
        sync_layout.addWidget(self.sync_status_lbl)

        try:
            if is_synced:
                path_str = SYNC_POINTER_PATH.read_text(encoding="utf-8").strip()
                if path_str:
                    self.sync_status_lbl.setText(path_str)
        except: pass

        # Buttons
        sync_btns = QHBoxLayout()
        sync_btns.setSpacing(10)
        self.btn_set_sync_dir = QPushButton("連結同步目錄 (Connect Sync Folder)")
        self.btn_set_sync_dir.setFixedHeight(44)
        self.btn_set_sync_dir.clicked.connect(self._set_sync_directory)
        sync_btns.addWidget(self.btn_set_sync_dir, stretch=1)

        self.btn_clear_sync = QPushButton("取消同步 (Disconnect)")
        self.btn_clear_sync.setFixedHeight(44)
        self.btn_clear_sync.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {s['text_secondary']};
                border: 1px solid {s['bg_input_border']};
                border-radius: 8px;
                font-size: 13px; font-weight: bold;
            }}
            QPushButton:hover {{ color: {s['text_primary']}; border-color: {s['text_secondary']}; }}
        """)
        self.btn_clear_sync.clicked.connect(self._clear_sync_directory)
        sync_btns.addWidget(self.btn_clear_sync)
        sync_layout.addLayout(sync_btns)

        body.addWidget(sync_card, stretch=3)

        # ─ Right: 安全提醒 ─
        sec_card = GlassCard()
        sec_layout = QVBoxLayout(sec_card)
        sec_layout.setContentsMargins(24, 24, 24, 24)
        sec_layout.setSpacing(12)

        shield_box = QFrame()
        shield_box.setStyleSheet(f"""
            background: {s['bg_input']}; border: 1px solid {s['bg_input_border']}; border-radius: 12px;
        """)
        shield_box.setFixedSize(56, 56)
        shield_bl = QVBoxLayout(shield_box)
        shield_bl.setContentsMargins(0, 0, 0, 0)
        shield_ic = ms_icon("shield", 26, s['text_secondary'])
        shield_ic.setFixedSize(56, 56)
        shield_bl.addWidget(shield_ic)
        sec_layout.addWidget(shield_box)

        sec_title = QLabel("安全性提醒")
        sec_title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {s['text_primary']}; background: transparent;")
        sec_layout.addWidget(sec_title)

        sec_body = QLabel(
            "同步目錄包含您的 AI API Key 設定，請確保該空間僅由您本人存取。\n\n"
            "建議使用加密的 NAS 磁碟或具備多重驗證的雲端硬碟。"
        )
        sec_body.setStyleSheet(f"font-size: 12px; color: {s['text_secondary']}; background: transparent; line-height: 1.5;")
        sec_body.setWordWrap(True)
        sec_layout.addWidget(sec_body)
        sec_layout.addStretch()

        body.addWidget(sec_card, stretch=2)
        layout.addLayout(body)

        # ── Bottom: Feature cards ─────────────────────────────
        feat_row = QHBoxLayout()
        feat_row.setSpacing(12)
        features = [
            ("manage_accounts", "靈魂情境", "同步自定義寫作風格與性格設定檔，讓 AI 在不同裝置間保持一致語氣。"),
            ("menu_book",       "詞彙同步", "專業術語與個人校正詞庫即時同步，多端協作不中斷。"),
            ("smart_toy",       "AI 記憶", "累積個人化 AI 學習數據，打造跨裝置的數位第二大腦。"),
        ]
        for icon, title, desc in features:
            fc = GlassCard()
            fl = QVBoxLayout(fc)
            fl.setContentsMargins(18, 18, 18, 18)
            fl.setSpacing(8)
            fi = ms_icon(icon, 20, s['text_secondary'])
            ft = QLabel(title)
            ft.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {s['text_primary']}; background: transparent;")
            fd = QLabel(desc)
            fd.setStyleSheet(f"font-size: 11px; color: {s['text_secondary']}; background: transparent;")
            fd.setWordWrap(True)
            fl.addWidget(fi)
            fl.addWidget(ft)
            fl.addWidget(fd)
            feat_row.addWidget(fc, stretch=1)
        layout.addLayout(feat_row)

        layout.addStretch()
        return page

    def _create_dashboard_page(self):
        from PyQt6.QtWidgets import QProgressBar
        s = self.skin
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # ── Header ────────────────────────────────────────────
        header_row = QHBoxLayout()
        header_left = QVBoxLayout()
        header_left.setSpacing(3)

        lbl_title = QLabel("嘴炮輸入法")
        lbl_title.setStyleSheet(f"font-size: 30px; font-weight: 800; color: {s['text_primary']}; letter-spacing: -1px; background: transparent;")
        lbl_subtitle = QLabel("即時狀態監控")
        lbl_subtitle.setStyleSheet(f"font-size: 12px; color: {s['text_secondary']}; background: transparent;")
        header_left.addWidget(lbl_title)
        header_left.addWidget(lbl_subtitle)
        header_row.addLayout(header_left)
        header_row.addStretch()

        from paths import VERSION_NAME
        version_badge = QLabel(f"  {VERSION_NAME}  ")
        version_badge.setStyleSheet(f"""
            color: {s['text_secondary']};
            background: {s['bg_card']};
            border: 1px solid {s['card_border']};
            border-radius: 6px;
            font-size: 10px;
            font-weight: bold;
            letter-spacing: 1px;
            padding: 4px 0;
        """)
        header_row.addWidget(version_badge, alignment=Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(header_row)

        # ── 四個權限狀態晶片 ──────────────────────────────────
        chips_row = QHBoxLayout()
        chips_row.setSpacing(10)

        self.light_acc = StatusChip("lock_open", "輔助功能",
            "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility")
        self.light_input = StatusChip("visibility", "輸入監聽",
            "x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent")
        self.light_mic = StatusChip("mic", "麥克風",
            "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone")

        # macOS 系統授權狀態晶片（固定顯示 Apple Silicon）
        chip_system = StatusChip("shield", "晶片組", "")
        chip_system.lbl_status.setText("Apple Silicon")
        chip_system.lbl_status.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {s['text_primary']}; background: transparent; border: none;")

        chips_row.addWidget(chip_system)
        chips_row.addWidget(self.light_acc)
        chips_row.addWidget(self.light_input)
        chips_row.addWidget(self.light_mic)
        layout.addLayout(chips_row)

        # ── 主要內容區：左側 AI 配置 + 右側統計 ──────────────
        main_row = QHBoxLayout()
        main_row.setSpacing(12)

        # ─ 左側：AI 配置卡片 ─
        ai_card = GlassCard()
        ai_layout = QVBoxLayout(ai_card)
        ai_layout.setContentsMargins(20, 18, 20, 18)
        ai_layout.setSpacing(14)

        # 卡片 header
        ai_header = QHBoxLayout()
        lbl_ai_title = QLabel("AI 配置")
        lbl_ai_title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {s['text_primary']}; background: transparent;")
        ai_header.addWidget(lbl_ai_title)
        ai_header.addStretch()

        self.lbl_status_stt = QLabel("MLX_WHISPER")
        self.lbl_status_stt.setStyleSheet(f"""
            color: {s['text_secondary']};
            background: {s['bg_input']};
            border: 1px solid {s['bg_input_border']};
            border-radius: 5px;
            font-size: 9px;
            font-weight: bold;
            letter-spacing: 1px;
            padding: 3px 8px;
        """)
        ai_header.addWidget(self.lbl_status_stt)
        ai_layout.addLayout(ai_header)

        # 模型大小選擇器（分段控制）
        lbl_model_size = QLabel("模型大小")
        lbl_model_size.setStyleSheet(f"font-size: 9px; font-weight: bold; letter-spacing: 1px; color: {s['text_secondary']}; text-transform: uppercase; background: transparent;")
        ai_layout.addWidget(lbl_model_size)

        seg_container = QWidget()
        seg_container.setStyleSheet(f"background: {s['bg_input']}; border-radius: 10px;")
        seg_layout = QHBoxLayout(seg_container)
        seg_layout.setContentsMargins(4, 4, 4, 4)
        seg_layout.setSpacing(2)

        current_model = self.config.get("whisper_model", "medium")
        self._model_seg_btns = {}
        for model_key, model_label in [("small", "Small"), ("medium", "Medium"), ("large", "Large")]:
            btn = QPushButton(model_label)
            btn.setCheckable(True)
            btn.setChecked(model_key == current_model)
            if btn.isChecked():
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {s['bg_card']};
                        color: {s['text_primary']};
                        border: none;
                        border-radius: 7px;
                        font-size: 12px;
                        font-weight: bold;
                        padding: 6px 0;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        color: {s['text_secondary']};
                        border: none;
                        font-size: 12px;
                        font-weight: bold;
                        padding: 6px 0;
                    }}
                    QPushButton:hover {{ color: {s['text_primary']}; }}
                """)
            self._model_seg_btns[model_key] = btn
            seg_layout.addWidget(btn)
        ai_layout.addWidget(seg_container)

        # 模型下載狀態指示（三個模型的燈號，沿用舊有 ModelStatusLight 介面）
        model_status_row = QHBoxLayout()
        model_status_row.setSpacing(8)
        self.light_model_small = ModelStatusLight("Small", "~500MB", "輕快版")
        self.light_model_medium = ModelStatusLight("Medium", "~1.5GB", "均衡版")
        self.light_model_large = ModelStatusLight("Large", "~3GB", "極致版")
        model_status_row.addWidget(self.light_model_small)
        model_status_row.addWidget(self.light_model_medium)
        model_status_row.addWidget(self.light_model_large)
        ai_layout.addLayout(model_status_row)

        # AI 潤飾開關列
        ai_refine_row = QWidget()
        ai_refine_row.setStyleSheet(f"background: {s['bg_input']}; border-radius: 8px;")
        refine_h = QHBoxLayout(ai_refine_row)
        refine_h.setContentsMargins(14, 10, 14, 10)

        refine_left = QVBoxLayout()
        refine_left.setSpacing(2)
        lbl_refine_title = QLabel("AI 潤飾")
        lbl_refine_title.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {s['text_primary']}; background: transparent;")
        lbl_refine_desc = QLabel("自動潤飾與語法修正")
        lbl_refine_desc.setStyleSheet(f"font-size: 11px; color: {s['text_secondary']}; background: transparent;")
        refine_left.addWidget(lbl_refine_title)
        refine_left.addWidget(lbl_refine_desc)
        refine_h.addLayout(refine_left)
        refine_h.addStretch()

        llm_on = self.config.get("llm_enabled", False)
        self.lbl_status_ai = QLabel("已開啟" if llm_on else "已關閉")
        self.lbl_status_ai.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {s['success'] if llm_on else s['text_secondary']}; background: transparent;")
        refine_h.addWidget(self.lbl_status_ai)
        ai_layout.addWidget(ai_refine_row)

        ai_layout.addStretch()
        main_row.addWidget(ai_card, stretch=3)

        # ─ 右側：統計卡片 ─
        right_col = QVBoxLayout()
        right_col.setSpacing(10)

        # 累計省下時間
        time_card = GlassCard()
        t_layout = QVBoxLayout(time_card)
        t_layout.setContentsMargins(18, 16, 18, 16)
        t_layout.setSpacing(4)
        lbl_t_cap = QLabel("累計省下時間")
        lbl_t_cap.setStyleSheet(f"font-size: 9px; font-weight: bold; letter-spacing: 1px; color: {s['text_secondary']}; background: transparent;")
        self.lbl_time_saved = QLabel("0")
        self.lbl_time_saved.setStyleSheet(f"font-size: 36px; font-weight: 800; color: {s['text_primary']}; letter-spacing: -1px; background: transparent;")
        lbl_t_unit = QLabel("小時")
        lbl_t_unit.setStyleSheet(f"font-size: 12px; color: {s['text_secondary']}; background: transparent;")
        self.lbl_total_chars_desc = QLabel("共辨識 0 字")
        self.lbl_total_chars_desc.setStyleSheet(f"font-size: 11px; color: {s['text_secondary']}; background: transparent;")
        t_layout.addWidget(lbl_t_cap)
        t_layout.addWidget(self.lbl_time_saved)
        t_layout.addWidget(lbl_t_unit)
        t_layout.addWidget(self.lbl_total_chars_desc)
        right_col.addWidget(time_card, stretch=2)

        # 今日錄音
        today_card = GlassCard()
        td_layout = QVBoxLayout(today_card)
        td_layout.setContentsMargins(18, 16, 18, 16)
        td_layout.setSpacing(4)
        lbl_td_cap = QLabel("今日錄音")
        lbl_td_cap.setStyleSheet(f"font-size: 9px; font-weight: bold; letter-spacing: 1px; color: {s['text_secondary']}; background: transparent;")
        self.lbl_today_count = QLabel("0")
        self.lbl_today_count.setStyleSheet(f"font-size: 36px; font-weight: 800; color: {s['text_primary']}; letter-spacing: -1px; background: transparent;")
        lbl_td_unit = QLabel("次")
        lbl_td_unit.setStyleSheet(f"font-size: 12px; color: {s['text_secondary']}; background: transparent;")
        self.lbl_today_chars = QLabel("辨識約 0 字")
        self.lbl_today_chars.setStyleSheet(f"font-size: 11px; color: {s['text_secondary']}; background: transparent;")
        td_layout.addWidget(lbl_td_cap)
        td_layout.addWidget(self.lbl_today_count)
        td_layout.addWidget(lbl_td_unit)
        td_layout.addWidget(self.lbl_today_chars)
        right_col.addWidget(today_card, stretch=2)

        main_row.addLayout(right_col, stretch=1)
        layout.addLayout(main_row)

        # ── 模型下載進度卡片（條件顯示）───────────────────────
        self.download_card = GlassCard()
        dl_layout = QVBoxLayout(self.download_card)
        dl_layout.setContentsMargins(20, 16, 20, 16)
        dl_layout.setSpacing(8)

        dl_header = QHBoxLayout()
        lbl_dl_title = QLabel("⬇  模型下載進度")
        lbl_dl_title.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {s['text_primary']}; background: transparent;")
        dl_header.addWidget(lbl_dl_title)
        dl_header.addStretch()
        self.lbl_download_pct = QLabel("0%")
        self.lbl_download_pct.setStyleSheet(f"font-size: 11px; color: {s['text_secondary']}; background: transparent;")
        dl_header.addWidget(self.lbl_download_pct)
        dl_layout.addLayout(dl_header)

        self.lbl_download_status = QLabel("等待模型載入...")
        self.lbl_download_status.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {s['text_primary']}; background: transparent;")
        dl_layout.addWidget(self.lbl_download_status)

        self.download_progress = QProgressBar()
        self.download_progress.setRange(0, 100)
        self.download_progress.setValue(0)
        self.download_progress.setFixedHeight(4)
        self.download_progress.setTextVisible(False)
        self.download_progress.setStyleSheet(f"""
            QProgressBar {{ background: {s['bg_input']}; border: none; border-radius: 2px; }}
            QProgressBar::chunk {{ background: {s['accent']}; border-radius: 2px; }}
        """)
        dl_layout.addWidget(self.download_progress)

        self.lbl_download_detail = QLabel("首次啟動需要下載 AI 模型，請確保網路暢通。")
        self.lbl_download_detail.setStyleSheet(f"font-size: 10px; color: {s['text_secondary']}; background: transparent;")
        dl_layout.addWidget(self.lbl_download_detail)

        layout.addWidget(self.download_card)
        self.download_card.setVisible(not self._is_model_present(self.config.get("whisper_model", "medium")))

        # ── 麥克風資訊卡（warmup 完成後顯示）─────────────────
        self.mic_info_card = GlassCard()
        mic_il = QHBoxLayout(self.mic_info_card)
        mic_il.setContentsMargins(20, 14, 20, 14)
        mic_il.setSpacing(14)

        mic_icon_box = QFrame()
        mic_icon_box.setFixedSize(40, 40)
        mic_icon_box.setStyleSheet(f"background: {s['bg_card']}; border: 1px solid {s['card_border']}; border-radius: 8px;")
        mic_icon_lyt = QHBoxLayout(mic_icon_box)
        mic_icon_lyt.setContentsMargins(0, 0, 0, 0)
        mic_icon_lyt.addWidget(ms_icon("mic", 18, s['text_secondary']))
        mic_il.addWidget(mic_icon_box)

        mic_text_v = QVBoxLayout()
        mic_text_v.setSpacing(2)
        lbl_mic_caption = QLabel("目前錄音裝置")
        lbl_mic_caption.setStyleSheet(f"font-size: 10px; color: {s['text_secondary']}; background: transparent;")
        self.lbl_mic_current = QLabel("—")
        self.lbl_mic_current.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {s['text_primary']}; background: transparent;")
        mic_text_v.addWidget(lbl_mic_caption)
        mic_text_v.addWidget(self.lbl_mic_current)
        mic_il.addLayout(mic_text_v, stretch=1)

        btn_mic_switch = QPushButton("切換設定")
        btn_mic_switch.setFixedHeight(32)
        btn_mic_switch.setObjectName("secondary")
        btn_mic_switch.clicked.connect(lambda: self._on_sidebar_changed(6))
        mic_il.addWidget(btn_mic_switch)

        layout.addWidget(self.mic_info_card)
        self.mic_info_card.setVisible(False)

        layout.addStretch()
        return page

    def _create_stt_llm_page(self):
        s = self.skin
        page = QScrollArea()
        page.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(24)
        layout.setContentsMargins(0, 0, 0, 0)

        # ── Header ────────────────────────────────────────────
        hdr_row = QHBoxLayout()
        lbl_hdr = QLabel("辨識 AI 設定")
        lbl_hdr.setStyleSheet(f"font-size: 22px; font-weight: 800; color: {s['text_primary']}; letter-spacing: -0.5px; background: transparent;")
        hdr_row.addWidget(lbl_hdr)
        hdr_row.addStretch()
        engine_badge = QLabel("  MLX WHISPER — Apple M Chip  ")
        engine_badge.setStyleSheet(f"""
            color: {s['text_secondary']};
            background: {s['bg_card']};
            border: 1px solid {s['card_border']};
            border-radius: 5px;
            font-size: 9px; font-weight: bold; letter-spacing: 1px;
            padding: 4px 0;
        """)
        hdr_row.addWidget(engine_badge, alignment=Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(hdr_row)

        # ── 模型選擇卡片區 ────────────────────────────────────
        sec_model = QLabel("模型選擇  /  MODEL SELECTION")
        sec_model.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {s['text_secondary']}; letter-spacing: 1px; background: transparent;")
        layout.addWidget(sec_model)

        model_cards_row = QHBoxLayout()
        model_cards_row.setSpacing(12)

        MODEL_META = {
            "large":  ("psychology",  "精準辨識", "Large",  "最高精準度，適合複雜環境與專業術語辨識。", "~3.0 GB"),
            "medium": ("balance",     "平衡模式", "Medium", "速度與精準的完美平衡，適合日常對話。",     "~1.5 GB"),
            "small":  ("bolt",        "輕量辨識", "Small",  "低延遲優先，適合簡單語句與快速記錄。",     "~500 MB"),
        }
        current_model = self.config.get("whisper_model", "medium")
        self._model_cards = {}

        for key, (icon, mode_label, name, desc, size) in MODEL_META.items():
            card = QFrame()
            card.setObjectName(f"model_card_{key}")
            is_active = (key == current_model)
            border_color = s['accent'] if is_active else s['card_border']
            card.setStyleSheet(f"""
                QFrame#model_card_{key} {{
                    background: {s['bg_card']};
                    border: 1.5px solid {border_color};
                    border-radius: 12px;
                }}
            """)
            card.setCursor(Qt.CursorShape.PointingHandCursor)

            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(18, 18, 18, 18)
            c_layout.setSpacing(8)

            # Icon box
            icon_box = QFrame()
            icon_box.setFixedSize(44, 44)
            icon_box.setStyleSheet(f"background: {s['bg_input']}; border-radius: 8px;")
            ib_l = QVBoxLayout(icon_box)
            ib_l.setContentsMargins(0, 0, 0, 0)
            ib_ic = ms_icon(icon, 22, s['text_primary'])
            ib_ic.setFixedSize(44, 44)
            ib_l.addWidget(ib_ic)
            c_layout.addWidget(icon_box)

            lbl_mode = QLabel(mode_label)
            lbl_mode.setStyleSheet(f"font-size: 9px; font-weight: bold; letter-spacing: 1px; color: {s['text_secondary']}; background: transparent;")
            c_layout.addWidget(lbl_mode)

            lbl_name = QLabel(name)
            lbl_name.setStyleSheet(f"font-size: 18px; font-weight: 800; color: {s['text_primary']}; letter-spacing: -0.5px; background: transparent;")
            c_layout.addWidget(lbl_name)

            lbl_desc = QLabel(desc)
            lbl_desc.setWordWrap(True)
            lbl_desc.setStyleSheet(f"font-size: 11px; color: {s['text_secondary']}; background: transparent;")
            c_layout.addWidget(lbl_desc)

            c_layout.addStretch()

            status_row = QHBoxLayout()
            is_ready = self._is_model_present(key)
            if is_active:
                active_badge = QLabel("ACTIVE")
                active_badge.setStyleSheet(f"""
                    font-size: 9px; font-weight: bold; letter-spacing: 1px;
                    color: {s['bg_window']};
                    background: {s['accent']};
                    border-radius: 4px;
                    padding: 2px 6px;
                """)
                status_row.addWidget(active_badge)
            else:
                placeholder = QLabel()
                status_row.addWidget(placeholder)
            status_row.addStretch()
            dl_lbl = QLabel("✓ 就緒" if is_ready else f"↓ {size}")
            dl_lbl.setStyleSheet(f"font-size: 10px; color: {s['success'] if is_ready else s['text_secondary']}; background: transparent;")
            status_row.addWidget(dl_lbl)
            c_layout.addLayout(status_row)

            card.setMinimumHeight(230)
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self._model_cards[key] = card
            model_cards_row.addWidget(card, stretch=1)

            # Click to select
            card.mousePressEvent = lambda e, k=key: self._select_model_card(k)

        layout.addLayout(model_cards_row)

        # ── 雙欄：左 API Keys ╱ 右 LLM 配置 ──────────────────
        two_col = QHBoxLayout()
        two_col.setSpacing(16)

        # ─ 左欄：API Keys ─
        keys_card = GlassCard()
        keys_layout = QVBoxLayout(keys_card)
        keys_layout.setContentsMargins(20, 18, 20, 18)
        keys_layout.setSpacing(12)

        lbl_keys_hdr = QLabel("使用大語言模型潤飾必填")
        lbl_keys_hdr.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {s['text_primary']}; background: transparent;")
        keys_layout.addWidget(lbl_keys_hdr)

        def _key_row(label, attr_name, prefix_hint):
            lbl = QLabel(label)
            lbl.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {s['text_secondary']}; background: transparent;")
            keys_layout.addWidget(lbl)
            field = QLineEdit()
            field.setEchoMode(QLineEdit.EchoMode.Password)
            field.setPlaceholderText(prefix_hint)
            field.setFixedHeight(36)
            keys_layout.addWidget(field)
            setattr(self, attr_name, field)

        _key_row("OpenAI API KEY",           "openai_key",     "sk-...")
        _key_row("Anthropic (Claude) API KEY","anthropic_key",  "sk-ant-...")
        _key_row("Gemini API KEY",            "gemini_key",     "AIzaSy...")
        _key_row("OpenRouter API KEY",        "openrouter_key", "sk-or-...")
        _key_row("通義千問 (Qwen) KEY",        "qwen_key",       "sk-...")
        _key_row("DeepSeek API KEY",          "deepseek_key",   "sk-...")
        keys_layout.addStretch()
        two_col.addWidget(keys_card, stretch=3)

        # ─ 右欄：LLM 配置 ─
        llm_card = GlassCard()
        llm_layout = QVBoxLayout(llm_card)
        llm_layout.setContentsMargins(20, 18, 20, 18)
        llm_layout.setSpacing(14)

        lbl_llm_hdr = QLabel("大語言模型潤飾（LLM REFINEMENT）")
        lbl_llm_hdr.setStyleSheet(f"font-size: 9px; font-weight: bold; letter-spacing: 1px; color: {s['text_secondary']}; background: transparent;")
        llm_layout.addWidget(lbl_llm_hdr)

        # 啟用開關列
        llm_toggle_row = QWidget()
        llm_toggle_row.setStyleSheet(f"background: {s['bg_input']}; border-radius: 8px;")
        lt_h = QHBoxLayout(llm_toggle_row)
        lt_h.setContentsMargins(14, 12, 14, 12)
        lt_left = QVBoxLayout()
        lt_left.setSpacing(2)
        lbl_lt_title = QLabel("啟用高階智慧潤飾與翻譯")
        lbl_lt_title.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {s['text_primary']}; background: transparent;")
        lbl_lt_desc = QLabel("自動修正標點符號與語氣")
        lbl_lt_desc.setStyleSheet(f"font-size: 11px; color: {s['text_secondary']}; background: transparent;")
        lt_left.addWidget(lbl_lt_title)
        lt_left.addWidget(lbl_lt_desc)
        lt_h.addLayout(lt_left)
        lt_h.addStretch()
        self.llm_enabled = ToggleSwitch(checked=self.config.get("llm_enabled", False))
        lt_h.addWidget(self.llm_enabled)
        llm_layout.addWidget(llm_toggle_row)

        # 模型提供商
        lbl_prov = QLabel("模型提供商（Provider）")
        lbl_prov.setStyleSheet(f"font-size: 11px; color: {s['text_secondary']}; background: transparent;")
        llm_layout.addWidget(lbl_prov)
        self.llm_engine = QComboBox()
        for eng in LLM_ENGINES:
            self.llm_engine.addItem(eng.capitalize() if eng != "openai" else "OpenAI", eng)
        llm_layout.addWidget(self.llm_engine)

        # 注入模式
        lbl_mode = QLabel("內容注入模式（Injection Mode）")
        lbl_mode.setStyleSheet(f"font-size: 11px; color: {s['text_secondary']}; background: transparent;")
        llm_layout.addWidget(lbl_mode)
        self.llm_mode = QComboBox()
        self.llm_mode.addItem("覆蓋原文（Replace）", "replace")
        self.llm_mode.addItem("快速附加（Fast）", "fast")
        llm_layout.addWidget(self.llm_mode)

        # 優先辨識語言
        lbl_lang = QLabel("優先辨識語言")
        lbl_lang.setStyleSheet(f"font-size: 11px; color: {s['text_secondary']}; background: transparent;")
        llm_layout.addWidget(lbl_lang)
        self.language = QComboBox()
        lang_meta = {"zh": "繁體中文", "en": "英文", "ja": "日文", "ko": "韓文", "yue": "粵語", "auto": "自動偵測"}
        for code, name in lang_meta.items():
            self.language.addItem(f"{name} ({code})", code)
        llm_layout.addWidget(self.language)

        llm_layout.addStretch()
        two_col.addWidget(llm_card, stretch=2)
        layout.addLayout(two_col)

        container.setLayout(layout)
        page.setWidget(container)
        return page

    def _select_model_card(self, selected_key: str):
        """點選模型卡片時更新選取狀態與 config。"""
        s = self.skin
        for key, card in self._model_cards.items():
            is_active = (key == selected_key)
            border_color = s['accent'] if is_active else s['card_border']
            card.setStyleSheet(f"""
                QFrame#model_card_{key} {{
                    background: {s['bg_card']};
                    border: 1.5px solid {border_color};
                    border-radius: 12px;
                }}
            """)
        self.config["whisper_model"] = selected_key

    def _create_soul_page(self):
        from PyQt6.QtWidgets import QTabWidget, QInputDialog
        s = self.skin
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # ── Header ────────────────────────────────────────────
        lbl_title = QLabel("靈魂設定")
        lbl_title.setStyleSheet(f"font-size: 30px; font-weight: 800; color: {s['text_primary']}; letter-spacing: -1px; background: transparent;")
        lbl_sub = QLabel("配置 AI 的人格模組與情境治理。")
        lbl_sub.setStyleSheet(f"font-size: 12px; color: {s['text_secondary']}; background: transparent;")
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_sub)

        # ── Tabs（底線樣式）──────────────────────────────────
        self.soul_tabs = QTabWidget()
        self.soul_tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background: transparent;
            }}
            QTabBar::tab {{
                background: transparent;
                color: {s['text_secondary']};
                padding: 10px 20px 10px 0;
                font-size: 14px;
                font-weight: bold;
                border: none;
                margin-right: 8px;
            }}
            QTabBar::tab:selected {{
                color: {s['text_primary']};
                border-bottom: 2px solid {s['accent']};
            }}
            QTabBar::tab:hover {{
                color: {s['text_primary']};
            }}
        """)

        # ── Tab 1：性格模式（兩欄佈局）───────────────────────
        scenario_tab = self._create_soul_scenario_tab()
        self.soul_tabs.addTab(scenario_tab, "性格模式")

        # ── Tab 2：基礎靈魂（純編輯器）───────────────────────
        base_tab = QWidget()
        base_layout = QVBoxLayout(base_tab)
        base_layout.setContentsMargins(0, 12, 0, 0)
        self.soul_prompt = QTextEdit()
        self.soul_prompt.setFont(QFont("Monaco", 12))
        self.soul_prompt.setPlaceholderText("輸入 AI 的基底靈魂提示詞（人格、風格、去贅詞規則）...")
        self.soul_prompt.setStyleSheet(f"""
            QTextEdit {{
                background: {s['bg_card']};
                border: 1px solid {s['card_border']};
                border-radius: 10px;
                color: {s['text_primary']};
                padding: 12px;
                font-family: Monaco, Menlo, monospace;
            }}
        """)
        base_layout.addWidget(self.soul_prompt)
        self.soul_tabs.addTab(base_tab, "基礎靈魂")

        layout.addWidget(self.soul_tabs)
        return page

    def _create_soul_scenario_tab(self):
        from PyQt6.QtWidgets import QInputDialog
        s = self.skin
        directory = SOUL_SCENARIO_DIR

        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 12, 0, 0)
        tab_layout.setSpacing(0)

        # ── 兩欄佈局 ──────────────────────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet(f"QSplitter::handle {{ background: {s['card_border']}; }}")

        # ─ 左欄：搜尋 + 列表 + 按鈕 ─
        left_panel = QWidget()
        left_panel.setStyleSheet(f"background: {s['bg_card']}; border-radius: 12px;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(8)

        # 搜尋框
        self._soul_search = QLineEdit()
        self._soul_search.setPlaceholderText("搜尋人格模組...")
        self._soul_search.setFixedHeight(36)
        self._soul_search.setStyleSheet(f"""
            QLineEdit {{
                background: {s['bg_input']};
                border: 1px solid {s['bg_input_border']};
                border-radius: 8px;
                color: {s['text_primary']};
                padding: 0 10px;
                font-size: 12px;
            }}
        """)
        left_layout.addWidget(self._soul_search)

        # 檔案列表
        self._soul_list = QListWidget()
        self._soul_list.setStyleSheet(f"""
            QListWidget {{
                background: transparent;
                border: none;
                color: {s['text_primary']};
                font-size: 13px;
                outline: none;
            }}
            QListWidget::item {{
                padding: 10px 8px;
                border-radius: 8px;
            }}
            QListWidget::item:selected {{
                background: {s['bg_input']};
                color: {s['text_primary']};
            }}
            QListWidget::item:hover {{
                background: {s['bg_input']};
            }}
        """)
        left_layout.addWidget(self._soul_list)

        # 底部按鈕
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_add = QPushButton("＋  新增項目")
        btn_add.setFixedHeight(36)
        btn_add.setStyleSheet(f"""
            QPushButton {{
                background: {s['bg_input']};
                color: {s['text_primary']};
                border: 1px solid {s['bg_input_border']};
                border-radius: 8px;
                font-size: 12px;
                font-weight: bold;
                padding: 0 12px;
            }}
            QPushButton:hover {{ background: {s['selection_bg']}; }}
        """)
        btn_del = QPushButton("⊟  刪除所選")
        btn_del.setFixedHeight(36)
        btn_del.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {s['danger']};
                border: 1px solid {s['danger']};
                border-radius: 8px;
                font-size: 12px;
                font-weight: bold;
                padding: 0 12px;
            }}
            QPushButton:hover {{ background: {s['danger']}; color: {s['bg_window']}; }}
        """)
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_del)
        left_layout.addLayout(btn_row)

        splitter.addWidget(left_panel)

        # ─ 右欄：編輯區 ─
        right_panel = QWidget()
        right_panel.setStyleSheet("background: transparent;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(12, 0, 0, 0)
        right_layout.setSpacing(8)

        # 右側 header
        editor_header = QHBoxLayout()
        self._soul_editor_label = QLabel("選擇左側檔案以開始編輯")
        self._soul_editor_label.setStyleSheet(f"""
            font-size: 12px; color: {s['text_secondary']}; background: transparent;
        """)
        editor_header.addWidget(self._soul_editor_label)
        editor_header.addStretch()
        btn_open_finder = QPushButton("  在 Finder 中打開資料夾")
        btn_open_finder.setFixedHeight(28)
        btn_open_finder.setStyleSheet(f"""
            QPushButton {{
                background: {s['bg_card']};
                color: {s['text_secondary']};
                border: 1px solid {s['card_border']};
                border-radius: 6px;
                font-size: 10px;
                padding: 0 10px;
            }}
            QPushButton:hover {{ color: {s['text_primary']}; }}
        """)
        btn_open_finder.clicked.connect(lambda: os.system(f"open '{directory}'"))
        editor_header.addWidget(btn_open_finder)
        right_layout.addLayout(editor_header)

        # 編輯器
        self._soul_editor = QTextEdit()
        self._soul_editor.setFont(QFont("Monaco", 12))
        self._soul_editor.setPlaceholderText("選擇左側的人格模組以編輯內容...")
        self._soul_editor.setStyleSheet(f"""
            QTextEdit {{
                background: {s['bg_card']};
                border: 1px solid {s['card_border']};
                border-radius: 10px;
                color: {s['text_primary']};
                padding: 14px;
                font-family: Monaco, Menlo, monospace;
            }}
        """)
        right_layout.addWidget(self._soul_editor)

        # 儲存按鈕
        self._soul_save_btn = QPushButton("儲存修改")
        self._soul_save_btn.setFixedHeight(36)
        self._soul_save_btn.hide()
        right_layout.addWidget(self._soul_save_btn)

        splitter.addWidget(right_panel)
        splitter.setSizes([260, 600])
        tab_layout.addWidget(splitter)

        # ── 邏輯 ─────────────────────────────────────────────
        def refresh(filter_text=""):
            self._soul_list.clear()
            if not directory.exists(): return
            for f in sorted(directory.glob("*.md")):
                if f.name == "default.md": continue
                if filter_text and filter_text.lower() not in f.name.lower(): continue
                item = QListWidgetItem(f"  {f.name}")
                item.setData(Qt.ItemDataRole.UserRole, f.name)
                self._soul_list.addItem(item)

        def on_item_clicked(item):
            fname = item.data(Qt.ItemDataRole.UserRole)
            fpath = directory / fname
            if fpath.exists():
                self._soul_editor.setPlainText(fpath.read_text(encoding="utf-8"))
                self._soul_editor_label.setText(f"編輯中   {fname}")
                self._soul_editor_label.setStyleSheet(f"""
                    font-size: 12px; color: {s['text_primary']}; font-weight: bold; background: transparent;
                """)
                self._soul_save_btn.show()

        def on_save():
            item = self._soul_list.currentItem()
            if not item: return
            fname = item.data(Qt.ItemDataRole.UserRole)
            fpath = directory / fname
            try:
                fpath.write_text(self._soul_editor.toPlainText(), encoding="utf-8")
            except Exception as e:
                QMessageBox.critical(self, "錯誤", f"儲存失敗：{e}")

        def on_add():
            name, ok = QInputDialog.getText(self, "新增人格模組", "請輸入模組名稱：")
            if not ok or not name.strip(): return
            filename = f"{name.strip()}.md"
            fpath = directory / filename
            if fpath.exists():
                QMessageBox.warning(self, "警告", "名稱已存在！"); return
            try:
                directory.mkdir(parents=True, exist_ok=True)
                fpath.write_text(f"# {name}\n\n[設定]\n- 語氣：\n- 行為：\n", encoding="utf-8")
                refresh()
                items = self._soul_list.findItems(f"  {filename}", Qt.MatchFlag.MatchExactly)
                if items:
                    self._soul_list.setCurrentItem(items[0])
                    on_item_clicked(items[0])
            except Exception as e:
                QMessageBox.critical(self, "錯誤", f"建立失敗：{e}")

        def on_delete():
            item = self._soul_list.currentItem()
            if not item: return
            fname = item.data(Qt.ItemDataRole.UserRole)
            reply = QMessageBox.question(self, "確認刪除", f"確定要刪除「{fname}」嗎？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                (directory / fname).unlink(missing_ok=True)
                refresh()
                self._soul_editor.clear()
                self._soul_editor_label.setText("選擇左側檔案以開始編輯")
                self._soul_editor_label.setStyleSheet(f"font-size: 12px; color: {s['text_secondary']}; background: transparent;")
                self._soul_save_btn.hide()

        def on_search(text):
            refresh(filter_text=text)

        self._soul_list.itemClicked.connect(on_item_clicked)
        self._soul_save_btn.clicked.connect(on_save)
        btn_add.clicked.connect(on_add)
        btn_del.clicked.connect(on_delete)
        self._soul_search.textChanged.connect(on_search)

        QTimer.singleShot(100, lambda: refresh())
        return tab

    def _create_file_list_tab(self, directory: Path, desc: str, is_json: bool = False):
        """Legacy method — kept for compatibility, not used in current UI."""
        return QWidget()

    def _create_vocab_mem_page(self):
        s = self.skin
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # ── Header ────────────────────────────────────────────
        hdr_row = QHBoxLayout()
        lbl_title = QLabel("詞彙與記憶管理")
        lbl_title.setStyleSheet(f"font-size: 30px; font-weight: 800; color: {s['text_primary']}; letter-spacing: -1px; background: transparent;")
        hdr_row.addWidget(lbl_title)
        hdr_row.addStretch()
        layout.addLayout(hdr_row)

        # ── Two columns ───────────────────────────────────────
        body = QHBoxLayout()
        body.setSpacing(16)

        # ─ Left: 私人詞庫 ─
        vocab_card = GlassCard()
        vl = QVBoxLayout(vocab_card)
        vl.setContentsMargins(20, 20, 20, 20)
        vl.setSpacing(12)

        v_hdr = QHBoxLayout()
        v_hdr.setSpacing(8)
        v_title = QLabel("私人詞庫")
        v_title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {s['text_primary']}; background: transparent;")
        v_hdr.addWidget(v_title)
        v_hdr.addStretch()

        self.btn_del_vocab = QPushButton("⊟  刪除已選")
        self.btn_del_vocab.setFixedHeight(32)
        self.btn_del_vocab.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {s['danger']};
                border: 1px solid {s['danger']}; border-radius: 8px;
                font-size: 12px; font-weight: bold; padding: 0 12px;
            }}
            QPushButton:hover {{ background: {s['danger']}; color: {s['bg_window']}; }}
        """)
        self.btn_del_vocab.clicked.connect(self._del_vocab)
        v_hdr.addWidget(self.btn_del_vocab)

        self.btn_add_vocab = QPushButton("+  新增")
        self.btn_add_vocab.setFixedHeight(32)
        self.btn_add_vocab.setStyleSheet(f"""
            QPushButton {{
                background: {s['accent']}; color: {s['btn_text']};
                border: none; border-radius: 8px;
                font-size: 12px; font-weight: bold; padding: 0 14px;
            }}
            QPushButton:hover {{ background: {s['accent_hover']}; }}
        """)
        self.btn_add_vocab.clicked.connect(self._add_vocab_dialog)
        v_hdr.addWidget(self.btn_add_vocab)
        vl.addLayout(v_hdr)

        vocab_search = QLineEdit()
        vocab_search.setPlaceholderText("搜尋專有名詞或技術術語...")
        vocab_search.setFixedHeight(36)
        vocab_search.textChanged.connect(self._search_vocab)
        vl.addWidget(vocab_search)

        self.vocab_list = QListWidget()
        vl.addWidget(self.vocab_list)

        # Hidden input (used by legacy _add_vocab)
        self.vocab_input = QLineEdit()
        self.vocab_input.hide()
        vl.addWidget(self.vocab_input)

        body.addWidget(vocab_card, stretch=3)

        # ─ Right: AI 學習清單 + 長期記憶 ─
        right_col = QVBoxLayout()
        right_col.setSpacing(16)

        # AI 學習清單
        ai_card = GlassCard()
        al = QVBoxLayout(ai_card)
        al.setContentsMargins(20, 20, 20, 20)
        al.setSpacing(12)

        ai_hdr = QHBoxLayout()
        ai_title = QLabel("AI 學習清單")
        ai_title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {s['text_primary']}; background: transparent;")
        ai_hdr.addWidget(ai_title)
        ai_hdr.addStretch()
        sync_badge = QLabel("SYNC_ACTIVE")
        sync_badge.setStyleSheet(f"""
            color: {s['text_secondary']}; background: {s['bg_input']};
            border: 1px solid {s['bg_input_border']}; border-radius: 4px;
            font-size: 9px; font-weight: bold; padding: 2px 6px;
        """)
        ai_hdr.addWidget(sync_badge)
        al.addLayout(ai_hdr)

        self.learned_list = QListWidget()
        self.learned_list.setFixedHeight(120)  # ~6 rows visible
        al.addWidget(self.learned_list)

        promote_row = QHBoxLayout()
        promote_row.addStretch()
        self.btn_delete_learned = QPushButton("刪除")
        self.btn_delete_learned.setFixedHeight(32)
        self.btn_delete_learned.setObjectName("danger")
        self.btn_delete_learned.clicked.connect(self._delete_learned_word)
        promote_row.addWidget(self.btn_delete_learned)
        self.btn_promote = QPushButton("升格至自訂詞庫")
        self.btn_promote.setFixedHeight(32)
        self.btn_promote.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {s['text_secondary']};
                border: 1px solid {s['bg_input_border']}; border-radius: 8px;
                font-size: 12px; padding: 0 14px;
            }}
            QPushButton:hover {{ color: {s['text_primary']}; border-color: {s['text_secondary']}; }}
        """)
        self.btn_promote.clicked.connect(self._promote_vocab)
        promote_row.addWidget(self.btn_promote)
        al.addLayout(promote_row)
        right_col.addWidget(ai_card)

        # 長期記憶快照
        mem_card = GlassCard()
        ml = QVBoxLayout(mem_card)
        ml.setContentsMargins(20, 20, 20, 20)
        ml.setSpacing(12)

        mem_hdr = QHBoxLayout()
        mem_title = QLabel("長期記憶快照")
        mem_title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {s['text_primary']}; background: transparent;")
        mem_hdr.addWidget(mem_title)
        mem_hdr.addStretch()
        self.lbl_mem_count = QLabel("")
        self.lbl_mem_count.setStyleSheet(f"font-size: 11px; color: {s['text_secondary']}; background: transparent;")
        mem_hdr.addWidget(self.lbl_mem_count)
        ml.addLayout(mem_hdr)

        # 摘要顯示區
        self.mem_summary_lbl = QLabel("（尚無摘要）")
        self.mem_summary_lbl.setWordWrap(True)
        self.mem_summary_lbl.setStyleSheet(
            f"font-size: 11px; color: {s['text_secondary']}; background: {s['bg_input']};"
            f"border-radius: 8px; padding: 8px; border: none;"
        )
        self.mem_summary_lbl.setMinimumHeight(50)
        ml.addWidget(self.mem_summary_lbl)

        self.mem_tree = QTreeWidget()
        self.mem_tree.setHeaderLabels(["時間", "快照"])
        self.mem_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        ml.addWidget(self.mem_tree)

        # Purge 按鈕列
        purge_row = QHBoxLayout()
        mem_inject_lbl = QLabel("記憶注入")
        mem_inject_lbl.setStyleSheet(f"font-size: 12px; color: {s['text_secondary']}; background: transparent;")
        self.memory_inject_toggle = ToggleSwitch(checked=self.config.get("memory_enabled", True))
        purge_row.addWidget(mem_inject_lbl)
        purge_row.addWidget(self.memory_inject_toggle)
        purge_row.addStretch()
        self.btn_purge_memory = QPushButton("壓縮本週記憶")
        self.btn_purge_memory.setFixedHeight(32)
        self.btn_purge_memory.setObjectName("danger")
        self.btn_purge_memory.clicked.connect(self._purge_memory)
        purge_row.addWidget(self.btn_purge_memory)
        ml.addLayout(purge_row)

        right_col.addWidget(mem_card, stretch=1)

        body.addLayout(right_col, stretch=2)
        layout.addLayout(body)
        return page

    def _create_stats_page(self):
        s = self.skin
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # ── Header ────────────────────────────────────────────
        hdr_row = QHBoxLayout()
        hdr_left = QVBoxLayout()
        hdr_left.setSpacing(3)
        lbl_title = QLabel("效能總覽")
        lbl_title.setStyleSheet(f"font-size: 30px; font-weight: 800; color: {s['text_primary']}; letter-spacing: -1px; background: transparent;")
        lbl_sub = QLabel("VoiceType4TW 語音轉錄精度與使用統計。")
        lbl_sub.setStyleSheet(f"font-size: 12px; color: {s['text_secondary']}; background: transparent;")
        hdr_left.addWidget(lbl_title)
        hdr_left.addWidget(lbl_sub)
        hdr_row.addLayout(hdr_left)
        hdr_row.addStretch()
        self.btn_refresh_stats = QPushButton("↺  重新整理數據")
        self.btn_refresh_stats.setFixedHeight(36)
        self.btn_refresh_stats.setStyleSheet(f"""
            QPushButton {{
                background: {s['bg_card']}; color: {s['text_primary']};
                border: 1px solid {s['card_border']}; border-radius: 8px;
                font-size: 13px; font-weight: bold; padding: 0 16px;
            }}
            QPushButton:hover {{ background: {s['selection_bg']}; }}
        """)
        self.btn_refresh_stats.clicked.connect(self._refresh_stats)
        hdr_row.addWidget(self.btn_refresh_stats)
        layout.addLayout(hdr_row)

        # ── Stats summary cards ───────────────────────────────
        summary_row = QHBoxLayout()
        summary_row.setSpacing(12)

        def _make_big_card(label, value_attr, unit, desc_attr):
            c = GlassCard()
            cl = QVBoxLayout(c)
            cl.setContentsMargins(20, 20, 20, 20)
            cl.setSpacing(4)
            lbl = QLabel(label)
            lbl.setStyleSheet(f"font-size: 11px; color: {s['text_secondary']}; letter-spacing: 1px; background: transparent;")
            val = QLabel("—")
            val.setStyleSheet(f"font-size: 40px; font-weight: 900; color: {s['text_primary']}; background: transparent;")
            desc = QLabel("—")
            desc.setStyleSheet(f"font-size: 11px; color: {s['text_secondary']}; background: transparent;")
            cl.addWidget(lbl)
            cl.addWidget(val)
            cl.addWidget(desc)
            setattr(self, value_attr, val)
            setattr(self, desc_attr, desc)
            return c

        summary_row.addWidget(_make_big_card("今日辨識次數", "lbl_stats_today_count", "", "lbl_stats_today_chars"), stretch=1)
        summary_row.addWidget(_make_big_card("累積節省時間 (小時)", "lbl_stats_time_saved", "min", "lbl_stats_total_chars"), stretch=1)
        layout.addLayout(summary_row)

        # ── Detailed stats table ──────────────────────────────
        table_card = GlassCard()
        tl = QVBoxLayout(table_card)
        tl.setContentsMargins(20, 20, 20, 20)
        tl.setSpacing(12)

        table_hdr = QLabel("數據統計")
        table_hdr.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {s['text_primary']}; background: transparent;")
        tl.addWidget(table_hdr)

        self.stats_tree = QTreeWidget()
        self.stats_tree.setHeaderLabels(["分析範圍", "會話總數", "錄音時長", "轉錄字數", "節省時間"])
        self.stats_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.stats_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.stats_tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.stats_tree.header().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.stats_tree.header().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.stats_tree.setAlternatingRowColors(False)
        self.stats_tree.setRootIsDecorated(False)
        tl.addWidget(self.stats_tree)
        layout.addWidget(table_card)

        layout.addStretch()
        return page

    def _create_general_page(self):
        from PyQt6.QtWidgets import QGridLayout
        s = self.skin
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # ── Header ────────────────────────────────────────────
        hdr_row = QHBoxLayout()
        hdr_left = QVBoxLayout()
        hdr_left.setSpacing(3)
        lbl_title = QLabel("系統設定")
        lbl_title.setStyleSheet(f"font-size: 30px; font-weight: 800; color: {s['text_primary']}; letter-spacing: -1px; background: transparent;")
        lbl_sub = QLabel("配置您的鈦金錄音環境，優化工作流程與硬體性能。")
        lbl_sub.setStyleSheet(f"font-size: 12px; color: {s['text_secondary']}; background: transparent;")
        hdr_left.addWidget(lbl_title)
        hdr_left.addWidget(lbl_sub)
        hdr_row.addLayout(hdr_left)
        hdr_row.addStretch()
        layout.addLayout(hdr_row)

        # ── Row 1: Hotkeys (left) + Diagnostics (right) ──────
        top_row = QHBoxLayout()
        top_row.setSpacing(16)

        # ─ 設定錄音按鍵 ─
        hotkey_card = GlassCard()
        hl = QVBoxLayout(hotkey_card)
        hl.setContentsMargins(20, 20, 20, 20)
        hl.setSpacing(14)

        hk_hdr = QHBoxLayout()
        hk_icon = ms_icon("keyboard", 18, s['text_secondary'])
        hk_title = QLabel("設定錄音按鍵")
        hk_title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {s['text_primary']}; background: transparent;")
        hk_hdr.addWidget(hk_icon)
        hk_hdr.addWidget(hk_title)
        hk_hdr.addStretch()
        hl.addLayout(hk_hdr)

        def _hotkey_row(label_text, key_attr, test_btn_attr, test_signal):
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(10)
            lbl = QLabel(label_text)
            lbl.setFixedWidth(130)
            lbl.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {s['text_primary']}; background: transparent;")
            btn = HotkeyRecorderButton(self.config.get(key_attr, ""))
            btn.setFixedHeight(36)
            test_btn = QPushButton("測試")
            test_btn.setFixedHeight(36)
            test_btn.setFixedWidth(54)
            test_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {s['btn_secondary_bg']}; color: {s['text_secondary']};
                    border: none; border-radius: 8px; font-size: 11px; font-weight: bold; padding: 0;
                }}
                QPushButton:hover {{ background: {s['selection_bg']}; color: {s['text_primary']}; }}
            """)
            setattr(self, test_btn_attr, test_btn)
            row.addWidget(lbl)
            row.addWidget(btn, stretch=1)
            row.addWidget(test_btn)
            return row, btn

        ptt_row, self.btn_ptt = _hotkey_row("PTT 按住通話", "hotkey_ptt", "btn_test_rec", None)
        self.btn_test_rec.pressed.connect(self.test_start.emit)
        self.btn_test_rec.released.connect(self.test_stop.emit)
        hl.addLayout(ptt_row)

        toggle_row_w, self.btn_toggle = _hotkey_row("Toggle 切換錄音", "hotkey_toggle", "btn_test_toggle", None)
        self.btn_test_toggle.clicked.connect(self.test_toggle.emit)
        hl.addLayout(toggle_row_w)

        llm_row_w, self.btn_llm = _hotkey_row("LLM 精煉轉寫", "hotkey_llm", "btn_test_llm", None)
        self.btn_test_llm.clicked.connect(self.test_llm.emit)
        hl.addLayout(llm_row_w)

        # ─ 分隔線 ─
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {s['bg_input_border']}; background: {s['bg_input_border']}; border: none; max-height: 1px;")
        hl.addWidget(sep)

        # ─ 麥克風選擇 ─
        mic_hdr = QHBoxLayout()
        mic_hdr.setSpacing(6)
        mic_hdr_icon = ms_icon("mic", 16, s['text_secondary'])
        mic_hdr_title = QLabel("麥克風選擇")
        mic_hdr_title.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {s['text_primary']}; background: transparent;")
        mic_hdr.addWidget(mic_hdr_icon)
        mic_hdr.addWidget(mic_hdr_title)
        mic_hdr.addStretch()
        hl.addLayout(mic_hdr)

        # 裝置選單列
        mic_dev_row = QHBoxLayout()
        mic_dev_row.setSpacing(8)
        mic_dev_lbl = QLabel("輸入裝置")
        mic_dev_lbl.setFixedWidth(130)
        mic_dev_lbl.setStyleSheet(f"font-size: 13px; color: {s['text_primary']}; background: transparent;")
        self.mic_device_combo = QComboBox()
        self.mic_device_combo.setFixedHeight(36)
        self._last_mic_device_names = []
        self._populate_mic_devices()
        btn_refresh_mic = QPushButton()
        btn_refresh_mic.setFixedSize(36, 36)
        btn_refresh_mic.setToolTip("重新偵測麥克風裝置")
        btn_refresh_mic.setLayout(QHBoxLayout())
        btn_refresh_mic.layout().setContentsMargins(0, 0, 0, 0)
        refresh_icon = ms_icon("refresh", 16, s['text_secondary'])
        btn_refresh_mic.layout().addWidget(refresh_icon)
        btn_refresh_mic.setStyleSheet(f"""
            QPushButton {{ background: {s['bg_input']}; border: 1px solid {s['bg_input_border']}; border-radius: 8px; }}
            QPushButton:hover {{ border-color: {s['text_secondary']}; }}
        """)
        btn_refresh_mic.clicked.connect(self._populate_mic_devices)
        mic_dev_row.addWidget(mic_dev_lbl)
        mic_dev_row.addWidget(self.mic_device_combo, stretch=1)
        mic_dev_row.addWidget(btn_refresh_mic)
        hl.addLayout(mic_dev_row)

        # 自動偵測插拔
        self._mic_poll_timer = QTimer(self)
        self._mic_poll_timer.timeout.connect(self._check_mic_devices_changed)
        self._mic_poll_timer.start(2000)

        # 音量感度列
        mic_gain_row = QHBoxLayout()
        mic_gain_row.setSpacing(8)
        mic_gain_lbl = QLabel("音量感度")
        mic_gain_lbl.setFixedWidth(130)
        mic_gain_lbl.setStyleSheet(f"font-size: 13px; color: {s['text_primary']}; background: transparent;")
        self.mic_gain_slider = QSlider(Qt.Orientation.Horizontal)
        self.mic_gain_slider.setRange(5, 200)
        self.mic_gain_slider.setValue(self.config.get("mic_gain", 50))
        self.mic_gain_slider.setFixedHeight(36)
        self.mic_gain_val_lbl = QLabel(f"×{self.config.get('mic_gain', 50)}")
        self.mic_gain_val_lbl.setFixedWidth(38)
        self.mic_gain_val_lbl.setStyleSheet(f"font-size: 12px; color: {s['text_secondary']}; background: transparent;")
        self.mic_gain_slider.valueChanged.connect(
            lambda v: self.mic_gain_val_lbl.setText(f"×{v}")
        )
        self.mic_gain_auto_toggle = ToggleSwitch(checked=self.config.get("mic_gain_auto", True))
        auto_lbl = QLabel("自動")
        auto_lbl.setStyleSheet(f"font-size: 12px; color: {s['text_secondary']}; background: transparent;")

        def _update_gain_slider_state(checked):
            self.mic_gain_slider.setEnabled(not checked)
            self.mic_gain_val_lbl.setEnabled(not checked)
        self.mic_gain_auto_toggle.toggled.connect(_update_gain_slider_state)
        _update_gain_slider_state(self.mic_gain_auto_toggle.isChecked())

        mic_gain_row.addWidget(mic_gain_lbl)
        mic_gain_row.addWidget(self.mic_gain_slider, stretch=1)
        mic_gain_row.addWidget(self.mic_gain_val_lbl)
        mic_gain_row.addWidget(auto_lbl)
        mic_gain_row.addWidget(self.mic_gain_auto_toggle)
        hl.addLayout(mic_gain_row)

        hl.addStretch()
        top_row.addWidget(hotkey_card, stretch=3)

        # ─ 診斷與修復 ─
        diag_card = GlassCard()
        dl = QVBoxLayout(diag_card)
        dl.setContentsMargins(20, 20, 20, 20)
        dl.setSpacing(10)

        d_hdr = QHBoxLayout()
        d_icon = ms_icon("build", 18, s['text_secondary'])
        d_title = QLabel("診斷與修復")
        d_title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {s['text_primary']}; background: transparent;")
        d_hdr.addWidget(d_icon)
        d_hdr.addWidget(d_title)
        d_hdr.addStretch()
        dl.addLayout(d_hdr)

        def _diag_card(icon, title, desc, action):
            dc = QPushButton()
            dc.setStyleSheet(f"""
                QPushButton {{
                    background: {s['bg_input']}; border: 1px solid {s['bg_input_border']};
                    border-radius: 10px; text-align: left; padding: 0;
                }}
                QPushButton:hover {{ border-color: {s['text_secondary']}; }}
            """)
            dc.setCursor(Qt.CursorShape.PointingHandCursor)
            dc.setFixedHeight(56)
            inner = QWidget(dc)
            inner.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            dcl = QHBoxLayout(inner)
            dcl.setContentsMargins(12, 8, 12, 8)
            dcl.setSpacing(12)

            # Icon box
            icon_box = QFrame(inner)
            icon_box.setFixedSize(40, 40)
            icon_box.setStyleSheet(f"""
                background: {s['bg_card']}; border: 1px solid {s['card_border']}; border-radius: 8px;
            """)
            icon_layout = QHBoxLayout(icon_box)
            icon_layout.setContentsMargins(0, 0, 0, 0)
            icon_lbl = ms_icon(icon, 18, s['text_secondary'])
            icon_lbl.setFixedSize(40, 40)
            icon_layout.addWidget(icon_lbl)
            dcl.addWidget(icon_box)

            text_v = QVBoxLayout()
            text_v.setSpacing(1)
            t = QLabel(title)
            t.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {s['text_primary']}; background: transparent;")
            d = QLabel(desc)
            d.setStyleSheet(f"font-size: 10px; color: {s['text_secondary']}; background: transparent;")
            text_v.addWidget(t)
            text_v.addWidget(d)
            dcl.addLayout(text_v)
            dcl.addStretch()

            # Fit inner widget to button
            dc.resizeEvent = lambda e, w=inner, b=dc: w.setGeometry(b.rect())
            dc.clicked.connect(action)
            return dc, dc

        mic_dc, self.btn_mic_test = _diag_card("mic_external_on", "麥克風測試與診斷", "檢查輸入音量與取樣頻率", self._run_mic_test)
        dl.addWidget(mic_dc)
        chk_dc, self.btn_run_self_check = _diag_card("health_and_safety", "系統自我檢測", "分析服務可用性與 API 連接", self._run_self_check)
        dl.addWidget(chk_dc)
        log_dc, self.btn_view_logs = _diag_card("terminal", "檢視詳細日誌", "開啟除錯日誌主面板", self._view_debug_log)
        dl.addWidget(log_dc)
        key_dc, self.btn_view_keystrike = _diag_card("history", "檢視熱鍵紀錄", "排查按鍵衝突與覆載狀態", self._view_keystrike_log)
        dl.addWidget(key_dc)

        dl.addStretch()
        top_row.addWidget(diag_card, stretch=2)
        layout.addLayout(top_row)

        # ── Row 2: 偏好設定 (left) + 進階 (right) ────────────
        bot_row = QHBoxLayout()
        bot_row.setSpacing(16)

        # ─ 偏好設定 ─
        pref_card = GlassCard()
        pl = QVBoxLayout(pref_card)
        pl.setContentsMargins(20, 20, 20, 20)
        pl.setSpacing(12)

        p_hdr = QHBoxLayout()
        p_icon = ms_icon("tune", 18, s['text_secondary'])
        p_title = QLabel("偏好設定")
        p_title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {s['text_primary']}; background: transparent;")
        p_hdr.addWidget(p_icon)
        p_hdr.addWidget(p_title)
        p_hdr.addStretch()
        pl.addLayout(p_hdr)

        def _toggle_item(label, config_key, default):
            item = QFrame()
            item.setStyleSheet(f"""
                QFrame {{
                    background: {s['bg_input']}; border: none;
                    border-radius: 10px;
                }}
            """)
            il = QHBoxLayout(item)
            il.setContentsMargins(14, 10, 14, 10)
            lbl = QLabel(label)
            lbl.setStyleSheet(f"font-size: 13px; color: {s['text_primary']}; background: transparent;")
            toggle = ToggleSwitch(self.config.get(config_key, default))
            il.addWidget(lbl)
            il.addStretch()
            il.addWidget(toggle)
            return item, toggle

        pref_grid = QGridLayout()
        pref_grid.setSpacing(10)

        ap_item, self.auto_paste = _toggle_item("結果自動貼上", "auto_paste", True)
        fb_item, self.show_floating_button = _toggle_item("顯示浮動按鈕", "show_floating_button", True)
        cs_item, self.completion_sound = _toggle_item("錄音完成播放音效", "completion_sound", True)
        dm_item, self.debug_mode = _toggle_item("啟用詳細日誌輸出", "debug_mode", False)

        pref_grid.addWidget(ap_item, 0, 0)
        pref_grid.addWidget(fb_item, 0, 1)
        pref_grid.addWidget(cs_item, 1, 0)
        pref_grid.addWidget(dm_item, 1, 1)
        pl.addLayout(pref_grid)

        bot_row.addWidget(pref_card, stretch=3)

        # ─ 咖啡版進階設定 ─
        adv_card = GlassCard()
        av = QVBoxLayout(adv_card)
        av.setContentsMargins(20, 20, 20, 20)
        av.setSpacing(12)

        # Hidden skin combo (kept for save/load compatibility)
        self.ui_skin_combo = QComboBox()
        self.ui_skin_combo.hide()
        for skin_key, skin_label in AVAILABLE_SKINS.items():
            self.ui_skin_combo.addItem(skin_label, skin_key)
        current_skin = self.config.get("ui_skin", "titanium")
        idx = list(AVAILABLE_SKINS.keys()).index(current_skin) if current_skin in AVAILABLE_SKINS else 0
        self.ui_skin_combo.setCurrentIndex(idx)
        av.addWidget(self.ui_skin_combo)

        adv_title = QLabel("咖啡版進階設定")
        adv_title.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {s['text_secondary']}; background: transparent;")
        av.addWidget(adv_title)

        self.showcase_mode = QCheckBox("靈魂展示版 - 單一靈魂輸出")
        self.showcase_mode.setChecked(self.config.get("showcase_mode", False))
        av.addWidget(self.showcase_mode)

        self.debug_demo_mode = QCheckBox("情境展示版 - 所有靈魂輸出")
        self.debug_demo_mode.setChecked(self.config.get("is_demo", False))
        av.addWidget(self.debug_demo_mode)

        self.output_prefix = QCheckBox("顯示靈魂前綴")
        self.output_prefix.setChecked(self.config.get("output_prefix", False))
        av.addWidget(self.output_prefix)



        av.addStretch()
        bot_row.addWidget(adv_card, stretch=2)
        layout.addLayout(bot_row)

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
        self.sync_status_lbl.setText(dir_path)

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
            self.sync_status_lbl.setText("本地存儲 (Local Only)")


    def _page_section_header(self, text):
        s = self.skin
        l = QLabel(text)
        l.setStyleSheet(f"font-weight: bold; font-size: 16px; color: {s['text_primary']}; background: transparent; margin-top: 10px; margin-bottom: 5px;")
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
        
        # 1. 語音辨識（MLX 固定，模型由卡片選取）
        self._select_model_card(self.config.get("whisper_model", "medium"))

        # 2. 語言與 AI 配置
        lang_val = self.config.get("language", "zh")
        lang_idx = self.language.findData(lang_val)
        if lang_idx >= 0: self.language.setCurrentIndex(lang_idx)
        else: self.language.setCurrentText(lang_val)
        
        self.llm_enabled.setChecked(self.config.get("llm_enabled", False))
        llm_eng_idx = self.llm_engine.findData(self.config.get("llm_engine", "ollama"))
        if llm_eng_idx >= 0: self.llm_engine.setCurrentIndex(llm_eng_idx)
        llm_mode_idx = self.llm_mode.findData(self.config.get("llm_mode", "replace"))
        if llm_mode_idx >= 0: self.llm_mode.setCurrentIndex(llm_mode_idx)
        
        # API Keys
        self.openai_key.setText(self.config.get("openai_api_key", ""))
        self.anthropic_key.setText(self.config.get("anthropic_api_key", ""))
        self.gemini_key.setText(self.config.get("gemini_api_key", ""))
        self.openrouter_key.setText(self.config.get("openrouter_api_key", ""))
        self.qwen_key.setText(self.config.get("qwen_api_key", ""))
        self.deepseek_key.setText(self.config.get("deepseek_api_key", ""))
        
        # 3. 系統設定 (Critical: fix UI overwriting disk with stale state)
        self.btn_ptt.key_str = self.config.get("hotkey_ptt", "alt_r")
        self.btn_toggle.key_str = self.config.get("hotkey_toggle", "f13")
        self.btn_llm.key_str = self.config.get("hotkey_llm", "f14")
        
        self.auto_paste.setChecked(self.config.get("auto_paste", True))
        self.show_floating_button.setChecked(self.config.get("show_floating_button", True))
        self.completion_sound.setChecked(self.config.get("completion_sound", True))
        self.debug_mode.setChecked(self.config.get("debug_mode", False))
        self.memory_inject_toggle.setChecked(self.config.get("memory_enabled", True))
        # 麥克風設定
        self._populate_mic_devices()
        self.mic_gain_slider.setValue(self.config.get("mic_gain", 50))
        self.mic_gain_auto_toggle.setChecked(self.config.get("mic_gain_auto", True))
        self.debug_demo_mode.setChecked(self.config.get("is_demo", False))
        self.output_prefix.setChecked(self.config.get("output_prefix", False))
        self.showcase_mode.setChecked(self.config.get("showcase_mode", False))

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
        s = self.skin
        llm_on = self.config.get("llm_enabled", False)
        self.lbl_status_ai.setText("已開啟" if llm_on else "已關閉")
        self.lbl_status_ai.setStyleSheet(
            f"font-size: 12px; font-weight: bold; color: {s['success'] if llm_on else s['text_secondary']}; background: transparent;"
        )

        eng = self.config.get("stt_engine", "mlx_whisper")
        self.lbl_status_stt.setText(eng.upper())

        # 檢查權限與模型狀態
        self._check_all_permissions()
        self._check_local_models()

    def update_download_progress(self, status: str, pct: int = -1, done: bool = False):
        """由 main.py 呼叫，更新模型下載 / 預熱進度卡片。
        pct = 0-100 實際進度, -1 = 不確定（indeterminate）, done=True 完成。
        """
        try:
            if done:
                self.download_progress.setRange(0, 100)
                self.download_progress.setValue(100)
                self.lbl_download_pct.setText("100%")
                QTimer.singleShot(600, self._on_warmup_done)
                return

            self.download_card.setVisible(True)
            self.lbl_download_status.setText(status)

            if pct < 0:
                # 不確定進度 → Qt 原生 indeterminate 動畫
                self.download_progress.setRange(0, 0)
                self.lbl_download_pct.setText("⏳")
            else:
                self.download_progress.setRange(0, 100)
                self.download_progress.setValue(pct)
                self.lbl_download_pct.setText(f"{pct}%")
        except Exception:
            pass

    def _on_warmup_done(self):
        """進度條完成後：隱藏 download_card，顯示麥克風資訊卡。"""
        try:
            self.download_card.setVisible(False)
            self._check_local_models()
            self._update_mic_info_card()
            self.mic_info_card.setVisible(True)
        except Exception:
            pass

    def _update_mic_info_card(self):
        """更新麥克風資訊卡顯示的裝置名稱。"""
        try:
            device_idx = self.config.get("mic_device")
            if device_idx is None:
                name = "系統預設 (System Default)"
            else:
                import sounddevice as sd
                dev = sd.query_devices(device_idx)
                name = dev['name'] if dev else f"裝置 #{device_idx}"
            self.lbl_mic_current.setText(name)
        except Exception:
            self.lbl_mic_current.setText("系統預設 (System Default)")

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

        from utils.permissions import check_accessibility, check_microphone
        
        # 1. Accessibility (also covers Input Monitoring for pynput)
        trusted = check_accessibility()
        self.light_acc.set_status(trusted)
        self.light_input.set_status(trusted)
        log.info(f"[PERM] Accessibility: {trusted}")

        # 2. Microphone
        mic_ok = check_microphone()
        self.light_mic.set_status(mic_ok)
        log.info(f"[PERM] Microphone Authorized: {mic_ok}")

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
            
            # support both faster-whisper and mlx-community naming structures
            # faster-whisper: models--Systran--faster-whisper-<size>
            # mlx-community: models--mlx-community--whisper-<size>-mlx (where large is large-v3-mlx)
            
            mlx_size = "large-v3" if size == "large" else size
            prefixes = [
                f"models--Systran--faster-whisper-{size}",
                f"models--mlx-community--whisper-{mlx_size}-mlx"
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
        try:
            from vocab.manager import load_all_learned_words, load_auto_memory
            memory = load_auto_memory()
            words = load_all_learned_words()
            for word in words:
                count = memory.get(word, 0)
                self.learned_list.addItem(f"{word} ({count})")
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
            entries = memory.get("entries", [])
            summary = memory.get("summary", "")

            # 摘要顯示
            self.mem_summary_lbl.setText(summary if summary else "（尚無摘要，壓縮後會在此顯示）")

            # 計數標籤
            self.lbl_mem_count.setText(f"{len(entries)} 筆原始記錄")

            for entry in reversed(entries):
                ts = entry.get("ts", "")[:16]
                text = (entry.get("llm") or entry.get("stt", ""))[:40]
                self.mem_tree.addTopLevelItem(QTreeWidgetItem([ts, text + ("..." if len(entry.get("llm") or entry.get("stt", "")) > 40 else "")]))
        except: pass

    def _purge_memory(self):
        from memory.manager import load_memory
        count = len(load_memory().get("entries", []))
        if count == 0:
            QMessageBox.information(self, "記憶壓縮", "目前沒有可壓縮的記憶條目。")
            return
        reply = QMessageBox.question(
            self, "確認壓縮記憶",
            f"將 {count} 筆原始記錄壓縮為摘要，並清除原始條目。\n"
            f"原始資料會備份至 archive 目錄，此操作不可復原。\n\n確定執行？",
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
            today_sessions = str(s['today']['sessions'])
            today_chars_txt = f"辨識約 {s['today']['chars']} 字"

            # Dashboard labels
            self.lbl_today_count.setText(today_sessions)
            self.lbl_today_chars.setText(today_chars_txt)

            # 計算省下時間 (以一般人打字速度 40字/分 計算)
            total_chars = s['total']['chars']
            saved_mins = total_chars / 40.0
            saved_txt = f"{saved_mins:.1f}" if saved_mins < 60 else f"{saved_mins/60.0:.1f}"
            total_desc = f"共辨識 {total_chars} 字"

            self.lbl_time_saved.setText(saved_txt)
            self.lbl_total_chars_desc.setText(total_desc)

            # Stats page labels (separate attributes to avoid overwrite)
            if hasattr(self, "lbl_stats_today_count"):
                self.lbl_stats_today_count.setText(today_sessions)
            if hasattr(self, "lbl_stats_today_chars"):
                self.lbl_stats_today_chars.setText(today_chars_txt)
            if hasattr(self, "lbl_stats_time_saved"):
                self.lbl_stats_time_saved.setText(saved_txt)
            if hasattr(self, "lbl_stats_total_chars"):
                self.lbl_stats_total_chars.setText(total_desc)

            def format_saved(chars):
                mins = chars / 40.0
                if mins < 60: return f"{mins:.1f}m"
                return f"{mins/60.0:.1f}h"

            self.stats_tree.addTopLevelItem(QTreeWidgetItem([
                "本日 (Today)", str(s["today"]["sessions"]), f"{s['today']['duration']}s", str(s["today"]["chars"]), format_saved(s["today"]["chars"])
            ]))
            self.stats_tree.addTopLevelItem(QTreeWidgetItem([
                "本週 (This Week)", str(s["week"]["sessions"]), f"{s['week']['duration']}s", str(s["week"]["chars"]), format_saved(s["week"]["chars"])
            ]))
            self.stats_tree.addTopLevelItem(QTreeWidgetItem([
                "累計 (Cumulative)", str(s["total"]["sessions"]), f"{s['total']['duration']}s", str(s["total"]["chars"]), format_saved(s["total"]["chars"])
            ]))
        except: pass

    def _add_vocab(self):
        word = self.vocab_input.text().strip()
        if not word: return
        from vocab.manager import add_custom_word
        add_custom_word(word)
        self.vocab_input.clear()
        self._refresh_vocab()

    def _add_vocab_dialog(self):
        from PyQt6.QtWidgets import QInputDialog
        word, ok = QInputDialog.getText(self, "新增詞彙", "請輸入新詞彙：")
        if ok and word.strip():
            from vocab.manager import add_custom_word
            add_custom_word(word.strip())
            self._refresh_vocab()

    def _search_vocab(self, text: str):
        for i in range(self.vocab_list.count()):
            item = self.vocab_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def _del_vocab(self):
        item = self.vocab_list.currentItem()
        if not item: return
        from vocab.manager import remove_custom_word
        remove_custom_word(item.text())
        self._refresh_vocab()

    def _save_action(self):
        self.config["stt_engine"] = "mlx_whisper"
        # whisper_model 由 _select_model_card() 即時寫入 self.config，這裡只確保同步
        self.config["language"] = self.language.currentData() or self.language.currentText()
        self.config["llm_enabled"] = self.llm_enabled.isChecked()
        self.config["llm_engine"] = self.llm_engine.currentData() or self.llm_engine.currentText()
        self.config["llm_mode"] = self.llm_mode.currentData() or self.llm_mode.currentText()
        self.config["openai_api_key"] = self.openai_key.text().strip()
        self.config["anthropic_api_key"] = self.anthropic_key.text().strip()
        self.config["gemini_api_key"] = self.gemini_key.text().strip()
        self.config["openrouter_api_key"] = self.openrouter_key.text().strip()
        self.config["qwen_api_key"] = self.qwen_key.text().strip()
        self.config["deepseek_api_key"] = self.deepseek_key.text().strip()
        self.config["hotkey_ptt"] = self.btn_ptt.key_str
        self.config["hotkey_toggle"] = self.btn_toggle.key_str
        self.config["hotkey_llm"] = self.btn_llm.key_str
        self.config["ui_skin"] = self.ui_skin_combo.currentData() or "titanium"
        
        log.info(f"[save] Writing UI hotkeys to config: PTT={self.config['hotkey_ptt']}, Toggle={self.config['hotkey_toggle']}, LLM={self.config['hotkey_llm']}")
        self.config["auto_paste"] = self.auto_paste.isChecked()
        self.config["completion_sound"] = self.completion_sound.isChecked()
        self.config["debug_mode"] = self.debug_mode.isChecked()
        self.config["separate_keystrike_log"] = self.debug_mode.isChecked()  # merged into debug toggle
        self.config["memory_enabled"] = self.memory_inject_toggle.isChecked()
        self.config["is_demo"] = self.debug_demo_mode.isChecked()
        self.config["output_prefix"] = self.output_prefix.isChecked()
        self.config["showcase_mode"] = self.showcase_mode.isChecked()
        self.config["show_floating_button"] = self.show_floating_button.isChecked()
        self.config["mic_device"] = self.mic_device_combo.currentData()
        self.config["mic_gain"] = self.mic_gain_slider.value()
        self.config["mic_gain_auto"] = self.mic_gain_auto_toggle.isChecked()

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

    def run(self):
        self.show()

    def _get_current_mic_names(self):
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            return [dev['name'] for dev in devices if dev['max_input_channels'] > 0]
        except Exception:
            return []

    def _check_mic_devices_changed(self):
        current = self._get_current_mic_names()
        if current != self._last_mic_device_names:
            self._populate_mic_devices()

    def _populate_mic_devices(self):
        prev_selection = self.mic_device_combo.currentData()
        self.mic_device_combo.clear()
        self.mic_device_combo.addItem("系統預設 (System Default)", None)
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            names = []
            for i, dev in enumerate(devices):
                if dev['max_input_channels'] > 0:
                    names.append(dev['name'])
                    self.mic_device_combo.addItem(f"{dev['name']}  (#{i})", i)
            self._last_mic_device_names = names
        except Exception as e:
            log.error(f"[mic] Failed to enumerate devices: {e}")
            self._last_mic_device_names = []
        # 還原上次的選擇（或從 config 讀取）
        restore = prev_selection if prev_selection is not None else self.config.get("mic_device")
        if restore is not None:
            idx = self.mic_device_combo.findData(restore)
            if idx >= 0:
                self.mic_device_combo.setCurrentIndex(idx)

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
        
        mic_dev = self.mic_device_combo.currentData()
        dev_name = self.mic_device_combo.currentText()
        try:
            recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='float32', device=mic_dev)
            
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
                    "偵測到【完全靜音】(Silence)。\n\n這通常代表 macOS TCC 權限異常，請嘗試在終端機執行：\ntccutil reset Microphone\n然後重啟 App。")
            elif energy < 1e-3:
                QMessageBox.warning(self, "測試警告", 
                    f"音訊能源過低 ({energy:.6f})。\n\n請檢查系統輸入音量設定。")
            else:
                QMessageBox.information(self, "測試成功",
                    f"成功接收音訊資料！\n裝置：{dev_name}\n能源強度: {energy:.6f}\n您的麥克風運作正常。")
                
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
