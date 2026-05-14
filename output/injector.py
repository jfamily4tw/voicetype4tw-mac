from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass

import pyperclip


@dataclass
class FrontmostApp:
    bundle_id: str | None = None
    pid: int | None = None
    name: str | None = None


class TextInjector:
    """
    Injects text into the currently focused input field
    by writing to clipboard and simulating Cmd+V.
    """

    def capture_frontmost_app(self) -> FrontmostApp | None:
        import platform

        if platform.system() != "Darwin":
            return None

        try:
            from AppKit import NSWorkspace

            app = NSWorkspace.sharedWorkspace().frontmostApplication()
            if not app:
                return None
            return FrontmostApp(
                bundle_id=app.bundleIdentifier(),
                pid=int(app.processIdentifier()),
                name=app.localizedName(),
            )
        except Exception:
            return None

    def inject(self, text: str, target_app: FrontmostApp | None = None) -> None:
        if not text:
            return
        pyperclip.copy(text)
        time.sleep(0.08)  # small delay to ensure clipboard is ready
        self._paste(target_app=target_app)

    def select_back(self, char_count: int) -> None:
        """往回選取 char_count 個字元（用於背景 LLM 替換）"""
        if char_count <= 0:
            return
            
        import platform
        if platform.system() == "Windows":
            from pynput.keyboard import Controller, Key
            kb = Controller()
            with kb.pressed(Key.shift):
                for _ in range(char_count):
                    kb.press(Key.left)
                    kb.release(Key.left)
        else:
            # macOS: Use AppleScript
            script = f"""
            tell application "System Events"
                repeat {char_count} times
                    key code 123 using shift down
                end repeat
            end tell
            """
            subprocess.run(["osascript", "-e", script], check=True)

    def _activate_target_app(self, target_app: FrontmostApp | None) -> None:
        import platform

        if platform.system() != "Darwin" or not target_app:
            return

        try:
            from AppKit import NSRunningApplication, NSApplicationActivateIgnoringOtherApps

            if target_app.pid:
                app = NSRunningApplication.runningApplicationWithProcessIdentifier_(target_app.pid)
                if app:
                    app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)
                    time.sleep(0.05)
                    return
        except Exception:
            pass

        if target_app.bundle_id:
            script = f'tell application id "{target_app.bundle_id}" to activate'
            try:
                subprocess.run(["osascript", "-e", script], check=False, timeout=2)
                time.sleep(0.05)
            except Exception:
                pass

    def _paste_with_keyboard(self) -> None:
        from pynput.keyboard import Controller, Key

        kb = Controller()
        with kb.pressed(Key.cmd):
            kb.press("v")
            kb.release("v")

    def _paste_with_ax(self, target_app: FrontmostApp | None) -> None:
        if not target_app or not target_app.pid:
            raise RuntimeError("No target app pid for AX paste")

        import ApplicationServices as AS

        app_ref = AS.AXUIElementCreateApplication(target_app.pid)
        command_keycode = 55
        v_keycode = 9

        rc = AS.AXUIElementPostKeyboardEvent(app_ref, 0, command_keycode, True)
        if rc != 0:
            raise RuntimeError(f"AX command-down failed: {rc}")
        rc = AS.AXUIElementPostKeyboardEvent(app_ref, ord("v"), v_keycode, True)
        if rc != 0:
            raise RuntimeError(f"AX v-down failed: {rc}")
        rc = AS.AXUIElementPostKeyboardEvent(app_ref, ord("v"), v_keycode, False)
        if rc != 0:
            raise RuntimeError(f"AX v-up failed: {rc}")
        rc = AS.AXUIElementPostKeyboardEvent(app_ref, 0, command_keycode, False)
        if rc != 0:
            raise RuntimeError(f"AX command-up failed: {rc}")

    def _paste_with_quartz(self) -> None:
        from Quartz import (
            CGEventCreateKeyboardEvent,
            CGEventPost,
            CGEventSetFlags,
            kCGEventFlagMaskCommand,
            kCGHIDEventTap,
        )

        command_keycode = 55
        v_keycode = 9

        cmd_down = CGEventCreateKeyboardEvent(None, command_keycode, True)
        v_down = CGEventCreateKeyboardEvent(None, v_keycode, True)
        v_up = CGEventCreateKeyboardEvent(None, v_keycode, False)
        cmd_up = CGEventCreateKeyboardEvent(None, command_keycode, False)

        CGEventSetFlags(cmd_down, kCGEventFlagMaskCommand)
        CGEventSetFlags(v_down, kCGEventFlagMaskCommand)
        CGEventSetFlags(v_up, kCGEventFlagMaskCommand)
        CGEventSetFlags(cmd_up, 0)

        for event in (cmd_down, v_down, v_up, cmd_up):
            CGEventPost(kCGHIDEventTap, event)
            time.sleep(0.01)

    def _paste_with_applescript(self) -> None:
        script = """
        tell application "System Events"
            keystroke "v" using command down
        end tell
        """
        subprocess.run(["osascript", "-e", script], check=True, timeout=2)

    def _paste(self, target_app: FrontmostApp | None = None) -> None:
        import platform
        if platform.system() == "Windows":
            from pynput.keyboard import Controller, Key
            kb = Controller()
            with kb.pressed(Key.ctrl):
                kb.press('v')
                kb.release('v')
        else:
            # macOS: restore focus to the original target app, then prefer direct keyboard events.
            self._activate_target_app(target_app)
            try:
                self._paste_with_ax(target_app)
                return
            except Exception:
                pass

            try:
                self._paste_with_applescript()
                return
            except Exception:
                pass

            try:
                self._paste_with_quartz()
                return
            except Exception:
                pass

            try:
                self._paste_with_keyboard()
                return
            except Exception:
                pass

            # Final fallback for environments where both AppleScript and Quartz fail.
            self._paste_with_applescript()
