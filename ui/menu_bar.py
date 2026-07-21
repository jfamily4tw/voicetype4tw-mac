"""
Cross-platform Menu Bar / System Tray manager.
"""
from typing import Callable, List, Dict
import platform
from config import load_config, save_config

class VoiceTypeMenuBar:
    """
    Unified Menu Bar logic. This class builds the menu structure 
    and handles state, delegating the actual rendering to TrayManager.
    """
    def __init__(self, config: dict, on_quit: Callable, on_toggle_llm: Callable,
                 on_set_translation: Callable, on_config_saved: Callable = None,
                 on_toggle_local_correction: Callable = None):
        self.config = config
        self.on_quit = on_quit
        self.on_toggle_llm = on_toggle_llm
        self.on_set_translation = on_set_translation
        self.on_config_saved = on_config_saved
        self.on_toggle_local_correction = on_toggle_local_correction
        self.tray = None  # Set by main.py

    def get_menu_items(self) -> List[Dict]:
        """Builds the full menu structure for the macOS menu bar."""
        from paths import EDITION, SOUL_SCENARIO_DIR
        llm_state = "ON" if self.config.get("llm_enabled") else "OFF"
        correction_state = "ON" if self.config.get("apple_local_correction_enabled") else "OFF"
        engine = self.config.get("stt_engine", "mlx_whisper")

        items = [
            {'label': "嘴炮輸入法", 'callback': None},
            {'label': "關於", 'callback': lambda _: self._show_about()},
            {'label': "---", 'callback': None},
            {'label': f"辨識引擎: {engine}", 'callback': None},
            {'label': "---", 'callback': None},
            {'label': f"本機快速校正 : {correction_state}", 'callback': self._toggle_local_correction},
            {'label': f"AI 潤飾/翻譯 : {llm_state}", 'callback': self._toggle_llm},
        ]

        # 版本功能分流
        if EDITION == "coffee":
            scenarios = [f.stem for f in SOUL_SCENARIO_DIR.glob("*.md")] if SOUL_SCENARIO_DIR.exists() else []
            items.append({'label': "靈魂情境", 'callback': None, 'submenu': self._build_scenario_menu(scenarios)})
        else:
            # Free 版：僅顯示底層靈魂（不可切換）
            items.append({'label': "底層靈魂", 'callback': None})

        items += [
            {'label': "快速翻譯", 'callback': None, 'submenu': [
                {'label': "翻譯成 英文", 'callback': lambda _: self._translate_en(), 'checked': (self.config.get("translation_lang") == "en")},
                {'label': "翻譯成 日文", 'callback': lambda _: self._translate_jp(), 'checked': (self.config.get("translation_lang") == "ja")},
                {'label': "恢復正常模式", 'callback': lambda _: self._translate_none(), 'checked': (self.config.get("translation_lang") is None)},
            ]},
            {'label': "---", 'callback': None},
            {'label': "偏好設定...", 'callback': lambda _: self._open_settings()},
            {'label': "---", 'callback': None},
            {'label': "結束", 'callback': lambda _: self._quit()},
        ]
        return items

    def _build_scenario_menu(self, scenarios):
        active = self.config.get("active_scenario", "default")
        items = [{'label': "預設 (基底靈魂)", 'callback': self._set_scenario, 'checked': (active == "default")}]
        for s in sorted(scenarios):
            if s == "default": continue
            # v2.7.32: 移除名稱開頭的 Emoji 標記
            import re
            clean_name = re.sub(r'^[\W_]+', '', s).strip()
            items.append({'label': clean_name, 'callback': self._set_scenario, 'checked': (active == s)})
        
        if not items:
            items.append({'label': "(無其他靈魂)", 'callback': None})
        return items

    def _build_format_menu(self, formats):
        active = self.config.get("active_format", "natural")
        items = [{'label': "自然排版 (無格式支援)", 'callback': self._set_format, 'checked': (active == "natural")}]
        for f in sorted(formats):
            if f == "natural": continue
            items.append({'label': f, 'callback': self._set_format, 'checked': (active == f)})
        return items

    def _build_template_menu(self, templates):
        if not templates:
            return [{'label': "(尚無儲存模板)", 'callback': None}]
        return [{'label': t, 'callback': self._use_template} for t in sorted(templates)]

    def _toggle_action_mode(self, _):
        # v2.8.4: Use internal config to avoid stale state if external reload is slow
        enabled = not self.config.get("action_mode", False)
        self.config["action_mode"] = enabled
        save_config(self.config)
        
        print(f"[menu] Action Mode toggled to: {enabled}")
        if hasattr(self, 'on_config_saved') and callable(self.on_config_saved):
            self.on_config_saved()
        self.refresh_ui()

    def _set_scenario(self, sender):
        latest = load_config()
        name = self._get_sender_text(sender)
        print(f"[menu] Scenario Selected: {name}")
        import re
        internal_name = re.sub(r'^[\W_]+', '', name).strip()
        if "基底靈魂" in name: internal_name = "default"
        
        latest["active_scenario"] = internal_name
        save_config(latest)
        self.config.clear()
        self.config.update(latest)
        
        if hasattr(self, 'on_config_saved') and callable(self.on_config_saved):
            self.on_config_saved()
        self.refresh_ui()

    def _set_format(self, sender):
        latest = load_config()
        name = self._get_sender_text(sender)
        print(f"[menu] Format Selected: {name}")
        import re
        internal_name = re.sub(r'^[\W_]+', '', name).strip()
        if "自然排版" in name: internal_name = "natural"
        
        latest["active_format"] = internal_name
        save_config(latest)
        self.config.clear()
        self.config.update(latest)
        
        if hasattr(self, 'on_config_saved') and callable(self.on_config_saved):
            self.on_config_saved()
        self.refresh_ui()

    def _use_template(self, sender):
        name = self._get_sender_text(sender)
        from paths import SOUL_TEMPLATE_DIR
        import json
        tpl_path = SOUL_TEMPLATE_DIR / f"{name}.json"
        if tpl_path.exists():
            with open(tpl_path, "r", encoding="utf-8") as f:
                output_text = json.load(f).get("output", "")
                if self.on_set_template:
                    self.on_set_template(output_text, name)

    def _toggle_llm(self, _):
        self.on_toggle_llm()
        self.refresh_ui()

    def _toggle_local_correction(self, _):
        if self.on_toggle_local_correction:
            self.on_toggle_local_correction()
        self.refresh_ui()

    def _translate_en(self): self.on_set_translation("en"); self.refresh_ui()
    def _translate_jp(self): self.on_set_translation("ja"); self.refresh_ui()
    def _translate_none(self): self.on_set_translation(None); self.refresh_ui()

    def _open_settings(self):
        import subprocess, sys, os
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        launcher = os.path.join(script_dir, "open_settings.py")
        subprocess.Popen([sys.executable, launcher], cwd=script_dir)

    def _show_about(self):
        # This still requires PyQt6
        from ui.about_window import AboutDialog
        dialog = AboutDialog(is_dark=self.config.get("dark_mode", True))
        dialog.exec()

    def _quit(self):
        self.on_quit()
        if self.tray: self.tray.stop()

    def refresh_ui(self):
        from PyQt6.QtCore import QTimer
        # Use singleShot to defer UI update until the current menu event loop finishes,
        # preventing Access Violation crashes on Windows when deleting the active QAction.
        QTimer.singleShot(0, self._deferred_refresh_ui)

    def _deferred_refresh_ui(self):
        full_items = self.get_menu_items()
        if self.tray:
            self.tray.update_menu(full_items)

    def set_recording(self):
        if self.tray and hasattr(self.tray, 'set_icon'): 
            self.tray.set_icon("🔴")

    def set_processing(self):
        if self.tray and hasattr(self.tray, 'set_icon'):
            self.tray.set_icon("⏳")

    def set_idle(self):
        if self.tray and hasattr(self.tray, 'set_icon'):
            self.tray.set_icon("🎙")

    def _get_sender_text(self, sender):
        """Helper to get text label from different tray item objects (rumps/pystray)."""
        if hasattr(sender, 'title'): # rumps.MenuItem
            return sender.title
        if hasattr(sender, 'text'): # pystray.MenuItem
            return sender.text
        # If it's already a string or something else
        return str(sender)
