import threading
import time
import platform
import queue
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

# v2.9.11: CGEventTap disable-reason constants (not always exposed by PyObjC)
_CG_TAP_DISABLED_BY_TIMEOUT = getattr(Quartz, "kCGEventTapDisabledByTimeout", 0xFFFFFFFE)
_CG_TAP_DISABLED_BY_USER_INPUT = getattr(Quartz, "kCGEventTapDisabledByUserInput", 0xFFFFFFFF)


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
        self._mode_lock = threading.Lock()  # v2.9.8: 保護 _active_mode 讀寫
        self._loop_thread: Optional[threading.Thread] = None

        # v2.9.8: Debounce — 每個 mode 的最後觸發時間，防止快速連按
        self._last_press_time: Dict[str, float] = {}
        self._DEBOUNCE_SEC = 0.3

        # macOS specific
        self._run_loop = None
        self._tap = None
        self._key_states: Dict[int, bool] = {}
        self._last_event_flags = 0

        # v2.9.11: CGEventTap auto-recovery
        self._tap_disable_count = 0          # 診斷用：tap 被停用次數
        self._watchdog_stop = threading.Event()
        self._watchdog_thread: Optional[threading.Thread] = None
        self._WATCHDOG_INTERVAL_SEC = 5.0
        self._WATCHDOG_INITIAL_REENABLES = 3
        # After the initial burst, keep retrying once per minute instead of
        # giving up forever. A transient macOS/TCC hiccup should not require
        # the user to restart the whole app.
        self._WATCHDOG_SLOW_RETRY_EVERY = 12

        # v2.9.11: Keystrike log 非同步寫檔 queue
        self._keystrike_queue: queue.Queue = queue.Queue(maxsize=10000)
        self._keystrike_writer_stop = threading.Event()
        self._keystrike_writer_thread: Optional[threading.Thread] = None

        # Windows specific
        self._win_listener = None

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
                    if len(parts) <= 1:
                        mask = 0

                self.key_combos[mode] = {"mask": mask, "keycode": main_keycode}
                print(f"[hotkey] Mapped: {mode} -> {name} (Mask: {mask}, Code: {main_keycode})")

    def start(self) -> None:
        if IS_WINDOWS:
            self._start_windows()
        else:
            self._start_macos()
            self._start_keystrike_writer()
            self._start_watchdog()

    def stop(self) -> None:
        if IS_WINDOWS:
            if self._win_listener:
                self._win_listener.stop()
                try:
                    self._win_listener.join()
                except Exception:
                    pass
        else:
            # v2.9.11: 停 watchdog 與 writer thread
            self._watchdog_stop.set()
            if self._watchdog_thread:
                self._watchdog_thread.join(timeout=1.0)
            self._keystrike_writer_stop.set()
            try:
                # 發一個 sentinel 讓 writer 跳出阻塞
                self._keystrike_queue.put_nowait(None)
            except queue.Full:
                pass
            if self._keystrike_writer_thread:
                self._keystrike_writer_thread.join(timeout=1.0)

            if self._run_loop:
                from Foundation import CFRunLoopStop
                CFRunLoopStop(self._run_loop)
            if self._loop_thread:
                self._loop_thread.join(timeout=0.5)
        self._loop_thread = None

    def _start_windows(self):
        try:
            from pynput import keyboard

            def on_press(key):
                k_str = key_to_str(key)
                self.log.debug(f"PRESSED: {k_str}")
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
        if self._loop_thread and self._loop_thread.is_alive():
            return
        self._loop_thread = threading.Thread(target=self._run_macos, daemon=True)
        self._loop_thread.start()

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

    # ── v2.9.11: CGEventTap 自癒機制 ────────────────────────────────
    def _re_enable_tap(self, reason: str):
        """Re-enable tap after OS disabled it. Also resets key states to avoid
        stale 'key held down' from events missed while tap was dead."""
        self._tap_disable_count += 1
        self.log.warning(
            f"[hotkey] CGEventTap disabled ({reason}). "
            f"Re-enabling (count={self._tap_disable_count})."
        )
        try:
            if self._tap:
                Quartz.CGEventTapEnable(self._tap, True)
        except Exception as e:
            self.log.error(f"[hotkey] Failed to re-enable tap: {e}")
            return
        # 全量 reset state — 避免「按住中被掉線」殘留假死
        self.reset_state()

    def _start_watchdog(self):
        """Layer 2: 5 秒檢查一次 tap 健康狀態。"""
        if self._watchdog_thread and self._watchdog_thread.is_alive():
            return
        self._watchdog_stop.clear()
        self._watchdog_thread = threading.Thread(
            target=self._watchdog_loop, name="hotkey-watchdog", daemon=True
        )
        self._watchdog_thread.start()
        self.log.info("[hotkey] Watchdog started.")

    def _watchdog_loop(self):
        """Watchdog: 若 tap 曾經正常、後來被停用，先密集重啟；仍無效時
        改成低頻持續重試，避免 log 洗版但不讓熱鍵永久假死。"""
        # 啟動後先等一輪，讓 tap 穩定
        if self._watchdog_stop.wait(self._WATCHDOG_INTERVAL_SEC):
            return
        consecutive_disabled = 0
        while not self._watchdog_stop.is_set():
            try:
                if self._tap is not None:
                    alive = Quartz.CGEventTapIsEnabled(self._tap)
                    if not alive:
                        consecutive_disabled += 1
                        if self._should_retry_disabled_tap(consecutive_disabled):
                            if consecutive_disabled > self._WATCHDOG_INITIAL_REENABLES:
                                self.log.warning(
                                    "[hotkey] Watchdog: tap still disabled after %d checks; "
                                    "retrying at low frequency."
                                    % consecutive_disabled
                                )
                            self._re_enable_tap("watchdog-detected")
                        elif consecutive_disabled == self._WATCHDOG_INITIAL_REENABLES + 1:
                            self.log.warning(
                                "[hotkey] Watchdog: tap 連續 %d 次無法啟用 — "
                                "改為低頻持續重試，避免需要重啟 app 才恢復。"
                                % self._WATCHDOG_INITIAL_REENABLES
                            )
                    else:
                        consecutive_disabled = 0
            except Exception as e:
                self.log.error(f"[hotkey] Watchdog check failed: {e}")
            if self._watchdog_stop.wait(self._WATCHDOG_INTERVAL_SEC):
                break

    def _should_retry_disabled_tap(self, consecutive_disabled: int) -> bool:
        """Return whether watchdog should try to re-enable a disabled tap now."""
        if consecutive_disabled <= self._WATCHDOG_INITIAL_REENABLES:
            return True
        return consecutive_disabled % self._WATCHDOG_SLOW_RETRY_EVERY == 0

    # ── v2.9.11: Keystrike log 非同步寫檔 ────────────────────────────
    def _start_keystrike_writer(self):
        if self._keystrike_writer_thread and self._keystrike_writer_thread.is_alive():
            return
        self._keystrike_writer_stop.clear()
        self._keystrike_writer_thread = threading.Thread(
            target=self._keystrike_writer_loop, name="keystrike-writer", daemon=True
        )
        self._keystrike_writer_thread.start()

    def _keystrike_writer_loop(self):
        from paths import KEYSTRIKE_LOG_PATH
        buf = []
        FLUSH_INTERVAL = 0.5
        last_flush = time.time()
        while True:
            try:
                timeout = max(0.05, FLUSH_INTERVAL - (time.time() - last_flush))
                item = self._keystrike_queue.get(timeout=timeout)
                if item is None:  # sentinel
                    break
                buf.append(item)
            except queue.Empty:
                pass
            except Exception:
                continue

            now = time.time()
            if buf and (now - last_flush >= FLUSH_INTERVAL or len(buf) >= 100):
                try:
                    with open(KEYSTRIKE_LOG_PATH, "a", encoding="utf-8") as f:
                        f.writelines(buf)
                except Exception:
                    pass
                buf = []
                last_flush = now

            if self._keystrike_writer_stop.is_set() and self._keystrike_queue.empty():
                break

        # final flush
        if buf:
            try:
                with open(KEYSTRIKE_LOG_PATH, "a", encoding="utf-8") as f:
                    f.writelines(buf)
            except Exception:
                pass

    def _macos_callback(self, proxy, type, event, refcon):
        import Quartz
        import datetime

        # v2.9.11 Layer 1: 攔截 tap 被系統停用事件，立刻重啟
        if type == _CG_TAP_DISABLED_BY_TIMEOUT:
            self._re_enable_tap("timeout")
            return event
        if type == _CG_TAP_DISABLED_BY_USER_INPUT:
            self._re_enable_tap("user-input")
            return event

        try:
            keycode = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
            flags = Quartz.CGEventGetFlags(event)
        except Exception:
            return event

        # v2.8.22: Deep Debug - Print all physical keystrokes if debug info is needed
        if self.config.get("debug_mode", False) and type == Quartz.kCGEventKeyDown:
            print(f"[hotkey] Received physical keycode: {keycode}, flags: {flags}")

        matched_mode = None

        if type in [Quartz.kCGEventKeyDown, Quartz.kCGEventKeyUp]:
            for mode, combo in self.key_combos.items():
                if combo["keycode"] == keycode:
                    if combo["mask"] == 0 or (flags & combo["mask"]) == combo["mask"]:
                        matched_mode = mode
                        break
        elif type == Quartz.kCGEventFlagsChanged:
            for mode, combo in self.key_combos.items():
                if combo["mask"] == 0 and combo["keycode"] == keycode:
                    matched_mode = mode
                    break

        # v2.9.11: Keystrike log 推入 queue，避免 callback 做檔案 I/O
        if self.config.get("separate_keystrike_log", False):
            try:
                ev_type = "PRESS" if type == Quartz.kCGEventKeyDown else "RELEASE" if type == Quartz.kCGEventKeyUp else "FLAGS_CHG"
                line = f"[{datetime.datetime.now().isoformat()}] RAW {ev_type} code={keycode} mode={matched_mode}\n"
                self._keystrike_queue.put_nowait(line)
            except queue.Full:
                pass
            except Exception:
                pass

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
        now = time.time()
        # v2.9.8: debounce — 短時間重複觸發直接忽略
        if now - self._last_press_time.get(mode, 0) < self._DEBOUNCE_SEC:
            print(f"[hotkey] Debounced press: {mode}")
            return
        self._last_press_time[mode] = now

        with self._mode_lock:
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
        if mode == "toggle":
            return
        with self._mode_lock:
            if self._active_mode == mode:
                self._active_mode = None
                threading.Thread(target=self.on_stop, args=(mode,), daemon=True).start()

    def reset_state(self):
        """External call to sync state when recording is manipulated via UI."""
        with self._mode_lock:
            self._active_mode = None
        self._key_states = {}
        self._last_press_time = {}
        self.log.debug("[hotkey] State reset")
