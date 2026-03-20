import threading
import time
from typing import Callable, Optional, Dict
import logging

log = logging.getLogger("voicetype.hotkey")

def key_to_str(key) -> str:
    return str(key).lower().replace("key.", "")

def str_to_key(key_str: str):
    return key_str

class HotkeyListener:
    def __init__(
        self,
        hotkey_configs: Dict[str, str],
        on_start: Callable[[str], None],
        on_stop: Callable[[str], None],
        config: dict = None
    ):
        self.configs = hotkey_configs
        self.on_start = on_start
        self.on_stop = on_stop
        self.config = config or {}
        self.log = log

        self._active_mode: Optional[str] = None
        self._loop_thread: Optional[threading.Thread] = None
        self._key_states: Dict[int, bool] = {}

        # Windows specific
        self._win_listener = None

    def start(self) -> None:
        self._start_windows()

    def stop(self) -> None:
        if self._win_listener:
            self._win_listener.stop()
            try:
                self._win_listener.join()
            except Exception:
                pass
        self._loop_thread = None

    def _start_windows(self):
        if self._loop_thread and self._loop_thread.is_alive():
            return
        self._loop_thread = threading.Thread(target=self._run_windows, daemon=True)
        self._loop_thread.start()

    def _run_windows(self):
        import ctypes
        import re

        user32 = ctypes.windll.user32

        # V68: Parse configurations to obtain exact Virtual Keys
        parsed_configs = {}
        for mode, cfg_key in self.configs.items():
            match = re.search(r'code:(\d+)', cfg_key, re.IGNORECASE)
            if match:
                parsed_configs[mode] = int(match.group(1))
            else:
                # Fallback VK mappings for legacy string configs
                key_map = {
                    "alt": 0x12, "alt_l": 0xA4, "alt_r": 0xA5,
                    "ctrl": 0x11, "ctrl_l": 0xA2, "ctrl_r": 0xA3,
                    "shift": 0x10, "shift_l": 0xA0, "shift_r": 0xA1,
                    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73, "f5": 0x74, "f6": 0x75,
                    "f7": 0x76, "f8": 0x77, "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B
                }
                parsed_configs[mode] = key_map.get(cfg_key.lower(), 0)

        self.log.info(f"[win_hotkey] Listener started. Parsed VKs: {parsed_configs}")

        # V68: Non-blocking pure Win32 API polling loop
        # We poll every 15ms. This avoids all Low-Level Keyboard Hook (WH_KEYBOARD_LL)
        # conflicts with OpenMP/CUDA/ctranslate2 message loops!
        while getattr(self, '_loop_thread', None) == threading.current_thread():
            for mode, vk in parsed_configs.items():
                if vk == 0: continue

                state = user32.GetAsyncKeyState(vk)
                is_pressed = (state & 0x8000) != 0

                was_pressed = self._key_states.get(vk, False)

                if is_pressed and not was_pressed:
                    self._key_states[vk] = True
                    self.log.debug(f"[win_hotkey] PRESSED: vk={vk} mode={mode}")
                    self._handle_press(mode)
                elif not is_pressed and was_pressed:
                    self._key_states[vk] = False
                    self.log.debug(f"[win_hotkey] RELEASED: vk={vk} mode={mode}")
                    self._handle_release(mode)

            time.sleep(0.015)

    def _handle_press(self, mode: str):
        # v2.8.6: Enhanced Toggle logic
        if mode == "toggle":
            if self._active_mode is None:
                self._active_mode = "toggle"
                print("[hotkey] Toggle START triggered")
                threading.Thread(target=self.on_start, args=("toggle",), daemon=True).start()
            elif self._active_mode == "toggle":
                self._active_mode = None
                print("[hotkey] Toggle STOP triggered")
                threading.Thread(target=self.on_stop, args=("toggle",), daemon=True).start()
        elif self._active_mode is None:
            self._active_mode = mode
            threading.Thread(target=self.on_start, args=(mode,), daemon=True).start()

    def _handle_release(self, mode: str):
        # Toggle mode ignores release (it stops on next press)
        if mode == "toggle":
            return
        if self._active_mode == mode:
            self._active_mode = None
            threading.Thread(target=self.on_stop, args=(mode,), daemon=True).start()

            # v2.8.27_V14: Prevent Windows from focusing the menu bar when Alt is released
            try:
                import ctypes
                user32 = ctypes.windll.user32
                user32.keybd_event(0x87, 0, 0, 0)  # F24 Down
                user32.keybd_event(0x87, 0, 2, 0)  # F24 Up
            except: pass

    def reset_state(self):
        """External call to sync state when recording is manipulated via UI."""
        self._active_mode = None
        self._key_states = {}
        self.log.debug("[hotkey] State reset")
