import threading
import time
import platform
from typing import Callable, Optional, Dict

IS_WINDOWS = platform.system() == "Windows"

def key_to_str(key) -> str:
    return str(key).lower().replace("key.", "")

def str_to_key(key_str: str):
    return key_str

def get_active_window_title() -> str:
    """Helper to get the title of the currently focused window."""
    try:
        if platform.system() == "Windows":
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
            return buff.value
        elif platform.system() == "Darwin":
            # macOS implementation using AppKit
            from AppKit import NSWorkspace
            active_app = NSWorkspace.sharedWorkspace().activeApplication()
            return active_app.get('NSApplicationName', '')
    except Exception:
        pass
    return ""

# Mapping common key names to macOS virtual key codes
KEY_NAME_TO_CODE = {
    "alt": 58, "alt_l": 58, "alt_r": 61,
    "cmd": 55, "cmd_l": 55, "cmd_r": 54,
    "ctrl": 59, "ctrl_l": 59, "ctrl_r": 62,
    "shift": 56, "shift_l": 56, "shift_r": 60,
    "space": 49, "enter": 36, "return": 36, "tab": 48, "esc": 53, "escape": 53,
    "backspace": 51, "delete": 117, "del": 117, "forward_delete": 117,
    "insert": 114, "ins": 114, "home": 115, "end": 119,
    "page_up": 116, "pgup": 116, "page_down": 121, "pgdn": 121,
    "up": 126, "down": 125, "left": 123, "right": 124,
    "print_screen": 105, "scroll_lock": 107, "pause": 113,
    "f1": 122, "f2": 120, "f3": 99, "f4": 118, "f5": 96, "f6": 97,
    "f7": 98, "f8": 100, "f9": 101, "f10": 109, "f11": 103, "f12": 111,
    "f13": 105, "f14": 107, "f15": 113, "f16": 106,
    "a": 0, "b": 11, "c": 8, "d": 2, "e": 14, "f": 3, "g": 5, "h": 4, "i": 34, "j": 38,
    "k": 40, "l": 37, "m": 46, "n": 45, "o": 31, "p": 35, "q": 12, "r": 15, "s": 1, "t": 17,
    "u": 32, "v": 9, "w": 13, "x": 7, "y": 16, "z": 6,
    "0": 29, "1": 18, "2": 19, "3": 20, "4": 21, "5": 23, "6": 22, "7": 26, "8": 28, "9": 25,
    "num_0": 82, "num_1": 83, "num_2": 84, "num_3": 85, "num_4": 86, "num_5": 87, "num_6": 88, "num_7": 89, "num_8": 91, "num_9": 92,
    "num_dot": 65, "num_enter": 76, "num_plus": 69, "num_minus": 78, "num_mul": 67, "num_div": 75, "num_equal": 81,
}

# Modifiers masks for comparison
import Quartz
MOD_MASKS = {
    "cmd": Quartz.kCGEventFlagMaskCommand,
    "alt": Quartz.kCGEventFlagMaskAlternate,
    "ctrl": Quartz.kCGEventFlagMaskControl,
    "shift": Quartz.kCGEventFlagMaskShift,
    "fn": Quartz.kCGEventFlagMaskSecondaryFn, # 0x800000
}

import logging
log = logging.getLogger("voicetype.hotkey")

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
        
        # macOS specific
        self._run_loop = None
        self._tap = None
        self._key_states: Dict[int, bool] = {}
        self._last_event_flags = 0
        self._pending_release_timers: Dict[str, threading.Timer] = {}
        
        # Windows specific
        self._win_listener = None
        self._mac_listener = None

        self.key_combos: Dict[str, Dict] = {} # mode -> {mask, keycode}
        if not IS_WINDOWS:
            self._refresh_key_map_macos()

    def _refresh_key_map_macos(self):
        import re
        self.key_combos = {}
        for mode, name in self.configs.items():
            name = name.lower()
            
            # v2.8.24: Support strict "code:XX" and legacy "(code:XX)" formats
            code_match = re.search(r'\(?code:(\d+)\)?', name)
            override_code = int(code_match.group(1)) if code_match else -1
            
            clean_name = re.sub(r'\(?code:\d+\)?', '', name).strip()
            parts = [p.strip() for p in clean_name.split("+") if p.strip()]
            mask = 0
            main_keycode = override_code
            
            for p in parts:
                if p in ["cmd", "command"]: mask |= Quartz.kCGEventFlagMaskCommand
                elif p in ["alt", "option"]: mask |= Quartz.kCGEventFlagMaskAlternate
                elif p in ["ctrl", "control"]: mask |= Quartz.kCGEventFlagMaskControl
                elif p in ["shift"]: mask |= Quartz.kCGEventFlagMaskShift
                elif p in ["fn"]: mask |= Quartz.kCGEventFlagMaskSecondaryFn
                elif p in KEY_NAME_TO_CODE:
                    code = KEY_NAME_TO_CODE[p]
                    if main_keycode == -1:
                        main_keycode = code
            
            if main_keycode != -1:
                # v2.8.15: If the main key is a modifier (single-key hotkey), the mask should be 0 
                # to trigger on FLAGS_CHANGED instead of KEY_DOWN
                if main_keycode in [54, 55, 56, 58, 59, 60, 61, 62, 63]:
                    # Check if any OTHER modifiers are in parts (e.g. cmd+shift)
                    # If it's JUST the modifier, mask=0
                    if len(parts) <= 1:
                        mask = 0
                
                self.key_combos[mode] = {"mask": mask, "keycode": main_keycode}
                print(f"[hotkey] Mapped: {mode} -> {name} (Mask: {mask}, Code: {main_keycode})")

    def start(self) -> None:
        if IS_WINDOWS:
            self._start_windows()
        else:
            self._start_macos()

    def stop(self) -> None:
        if IS_WINDOWS:
            if self._win_listener:
                self._win_listener.stop()
                try:
                    self._win_listener.join()
                except Exception:
                    pass
        else:
            if self._mac_listener:
                self._mac_listener.stop()
                try:
                    self._mac_listener.join()
                except Exception:
                    pass
                self._mac_listener = None
            if self._run_loop:
                from Foundation import CFRunLoopStop
                CFRunLoopStop(self._run_loop)
            if self._loop_thread:
                self._loop_thread.join(timeout=0.5)
        self._loop_thread = None

    def _start_windows(self):
        # ... (Windows logic remains same or update if needed)
        try:
            from pynput import keyboard
            
            def on_press(key):
                k_str = key_to_str(key)
                self.log.debug(f"PRESSED: {k_str}")
                # Simple single key support for now on Windows
                for mode, cfg_key in self.configs.items():
                    if cfg_key.lower() == k_str:
                        self._handle_press(mode)

            def on_release(key):
                k_str = key_to_str(key)
                for mode, cfg_key in self.configs.items():
                    if cfg_key.lower() == k_str:
                        self._handle_release(mode)

            self._win_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
            self._win_listener.start()
        except ImportError: pass

    def _start_macos(self):
        self._start_macos_pynput_fallback()
        if self._loop_thread and self._loop_thread.is_alive():
            return
        self._loop_thread = threading.Thread(target=self._run_macos, daemon=True)
        self._loop_thread.start()

    def _normalize_hotkey_name(self, value: str) -> str:
        import re

        value = (value or "").lower().strip()
        code_match = re.search(r'\(?code:(\d+)\)?', value)
        if code_match:
            code = int(code_match.group(1))
            code_to_name = {
                54: "cmd_r",
                55: "cmd",
                56: "shift",
                58: "alt",
                59: "ctrl",
                60: "shift_r",
                61: "alt_r",
                62: "ctrl_r",
                63: "fn",
                105: "f13",
                107: "f14",
                113: "f15",
            }
            return code_to_name.get(code, f"code:{code}")
        return value

    def _start_macos_pynput_fallback(self):
        try:
            from pynput import keyboard

            def on_press(key):
                k_str = key_to_str(key)
                for mode, cfg_key in self.configs.items():
                    if self._normalize_hotkey_name(cfg_key) == k_str:
                        self._handle_press(mode)

            def on_release(key):
                k_str = key_to_str(key)
                for mode, cfg_key in self.configs.items():
                    if self._normalize_hotkey_name(cfg_key) == k_str:
                        self._handle_release(mode)

            self._mac_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
            self._mac_listener.start()
            self.log.info("macOS pynput fallback listener started.")
        except Exception as e:
            self.log.warning(f"macOS pynput fallback listener failed: {e}")

    def _run_macos(self):
        import Quartz
        from Foundation import CFRunLoopGetCurrent, kCFRunLoopDefaultMode, CFRunLoopRunInMode
        self._run_loop = CFRunLoopGetCurrent()
        event_mask = (1 << Quartz.kCGEventKeyDown) | (1 << Quartz.kCGEventKeyUp) | (1 << Quartz.kCGEventFlagsChanged)
        self._tap = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap, Quartz.kCGHeadInsertEventTap,
            Quartz.kCGEventTapOptionListenOnly, event_mask, self._macos_callback, None
        )
        if not self._tap:
            self.log.error("Failed to create macOS event tap.")
            return
        run_loop_source = Quartz.CFMachPortCreateRunLoopSource(None, self._tap, 0)
        Quartz.CFRunLoopAddSource(self._run_loop, run_loop_source, kCFRunLoopDefaultMode)
        Quartz.CGEventTapEnable(self._tap, True)
        self.log.info("macOS Quartz listener started.")
        CFRunLoopRunInMode(kCFRunLoopDefaultMode, 10e10, False)

    def _macos_callback(self, proxy, type, event, refcon):
        import Quartz
        import datetime
        from paths import KEYSTRIKE_LOG_PATH
        
        keycode = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
        flags = Quartz.CGEventGetFlags(event)
        
        # v2.8.22: Deep Debug - Print all physical keystrokes if debug info is needed
        # We only print this if the user is actively debugging to avoid log spam
        if self.config.get("debug_mode", False) and type == Quartz.kCGEventKeyDown:
            print(f"[hotkey] Received physical keycode: {keycode}, flags: {flags}")
        
        matched_mode = None
        
        if type in [Quartz.kCGEventKeyDown, Quartz.kCGEventKeyUp]:
            # v2.8.20: Allow matching even if mask is 0 (for standard keys like F13, F14)
            for mode, combo in self.key_combos.items():
                if combo["keycode"] == keycode:
                    # If mask is 0, it means no modifiers are required
                    if combo["mask"] == 0 or (flags & combo["mask"]) == combo["mask"]:
                        matched_mode = mode
                        break
        elif type == Quartz.kCGEventFlagsChanged:
            # For modifier-only hotkeys (mask=0)
            for mode, combo in self.key_combos.items():
                if combo["mask"] == 0 and combo["keycode"] == keycode:
                    matched_mode = mode
                    break

        # Log ALL raw key interactions if keystrike log is active (v2.8.14-dev)
        if self.config.get("separate_keystrike_log", False):
            try:
                ev_type = "PRESS" if type == Quartz.kCGEventKeyDown else "RELEASE" if type == Quartz.kCGEventKeyUp else "FLAGS_CHG"
                with open(KEYSTRIKE_LOG_PATH, "a") as f:
                    f.write(f"[{datetime.datetime.now().isoformat()}] RAW {ev_type} code={keycode} mode={matched_mode}\n")
            except: pass

        if matched_mode:
            if type == Quartz.kCGEventKeyDown:
                if not self._key_states.get(keycode, False):
                    self._key_states[keycode] = True
                    self._handle_press(matched_mode)
            elif type == Quartz.kCGEventKeyUp:
                if self._key_states.get(keycode, False):
                    self._key_states[keycode] = False
                    self._handle_release(matched_mode)
            elif type == Quartz.kCGEventFlagsChanged:
                is_pressed = False
                # Precision mapping for common Magic Keys
                if keycode in [58, 61]: # alt / alt_r
                    is_pressed = bool(flags & Quartz.kCGEventFlagMaskAlternate)
                elif keycode in [56, 60]: # shift / shift_r
                    is_pressed = bool(flags & Quartz.kCGEventFlagMaskShift)
                elif keycode in [59, 62]: # ctrl / ctrl_r
                    is_pressed = bool(flags & Quartz.kCGEventFlagMaskControl)
                elif keycode in [55, 54]: # cmd / cmd_r
                    is_pressed = bool(flags & Quartz.kCGEventFlagMaskCommand)
                elif keycode == 63: # fn
                    is_pressed = bool(flags & Quartz.kCGEventFlagMaskSecondaryFn)
                
                was_pressed = self._key_states.get(keycode, False)
                if is_pressed and not was_pressed:
                    self._key_states[keycode] = True
                    self._handle_press(matched_mode)
                elif not is_pressed and was_pressed:
                    self._key_states[keycode] = False
                    self._handle_release(matched_mode)
        
        return event

    def _handle_press(self, mode: str):
        timer = self._pending_release_timers.pop(mode, None)
        if timer:
            timer.cancel()

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
        combo = self.key_combos.get(mode, {})
        is_modifier_only = combo.get("mask") == 0 and combo.get("keycode") in [54, 55, 56, 58, 59, 60, 61, 62, 63]
        if is_modifier_only:
            timer = self._pending_release_timers.pop(mode, None)
            if timer:
                timer.cancel()

            def confirm_release():
                if self._active_mode == mode:
                    self._active_mode = None
                    threading.Thread(target=self.on_stop, args=(mode,), daemon=True).start()
                self._pending_release_timers.pop(mode, None)

            timer = threading.Timer(0.12, confirm_release)
            timer.daemon = True
            self._pending_release_timers[mode] = timer
            timer.start()
            return

        if self._active_mode == mode:
            self._active_mode = None
            threading.Thread(target=self.on_stop, args=(mode,), daemon=True).start()
    def reset_state(self):
        """External call to sync state when recording is manipulated via UI."""
        for timer in self._pending_release_timers.values():
            timer.cancel()
        self._pending_release_timers = {}
        self._active_mode = None
        self._key_states = {}
        self.log.debug("[hotkey] State reset")
