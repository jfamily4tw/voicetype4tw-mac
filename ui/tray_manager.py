import os
import sys
import platform
import threading
from typing import Callable, List, Dict, Optional

import logging

IS_WINDOWS = sys.platform == "win32"

class TrayManager:
    """
    Windows system tray manager using QSystemTrayIcon (PyQt6).
    """
    def __init__(self, title: str, icon_path: str, menu_items: List[Dict]):
        self.title = title
        self.icon_path = icon_path
        self.menu_items = menu_items
        self._tray = None
        self._qt_menu = None

    def start(self, on_tick: Optional[Callable] = None):
        self._start_windows()

    def stop(self):
        if self._tray:
            self._tray.stop()

    def stop_ticker(self):
        """No-op on Windows (Qt handles its own event loop)."""
        pass

    def update_menu(self, menu_items: List[Dict]):
        self.menu_items = menu_items
        self._update_windows_menu()

    def _start_windows(self):
        try:
            from PyQt6.QtWidgets import QSystemTrayIcon, QApplication
            from PyQt6.QtGui import QIcon
            t_log = logging.getLogger("voicetype.tray")

            t_log.info(f"[tray] Starting Windows Tray (QSystemTrayIcon) with icon: {self.icon_path}")

            app = QApplication.instance()
            if not app:
                t_log.error("[tray] Critical: QApplication not found. Tray cannot start.")
                return

            if not QSystemTrayIcon.isSystemTrayAvailable():
                t_log.error("[tray] Critical: System tray is not available on this system.")
                return

            icon = QIcon(self.icon_path)
            self._tray = QSystemTrayIcon(icon, app)
            self._tray.setToolTip(self.title)

            menu = self._build_qt_menu(self.menu_items)
            self._tray.setContextMenu(menu)

            self._tray.show()
            t_log.info("[tray] QSystemTrayIcon shown successfully.")

            # Store the menu to prevent garbage collection
            self._qt_menu = menu

        except Exception as e:
            import traceback
            msg = f"[tray] CRITICAL Windows QSystemTrayIcon error: {e}\n{traceback.format_exc()}"
            print(msg)
            logging.getLogger("voicetype").error(msg)

    def _update_windows_menu(self):
        if self._tray:
            try:
                menu = self._build_qt_menu(self.menu_items)
                self._tray.setContextMenu(menu)
                self._qt_menu = menu
                logging.getLogger("voicetype.tray").debug("[tray] Windows tray menu updated.")
            except Exception as e:
                print(f"[tray] Failed to update tray menu: {e}")

    def _build_qt_menu(self, items, parent=None):
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QAction

        menu = QMenu(parent)
        for item in items:
            label = item.get('label', '')
            callback = item.get('callback')
            checked = item.get('checked', None)
            submenu = item.get('submenu')

            if label == "---":
                menu.addSeparator()
                continue

            if submenu:
                sub_menu_obj = self._build_qt_menu(submenu, menu)
                sub_menu_obj.setTitle(label)
                menu.addMenu(sub_menu_obj)
                continue

            action = QAction(label, menu)

            if checked is not None:
                action.setCheckable(True)
                action.setChecked(bool(checked))

            if callback:
                def make_handler(cb, lbl=label):
                    def safe_handler():
                        try:
                            logging.getLogger("voicetype.tray").debug(f"[tray] QAction clicked: {lbl}")
                            cb(action)
                        except Exception as e:
                            import traceback
                            msg = f"[tray] Error in Qt callback for '{lbl}': {e}\n{traceback.format_exc()}"
                            print(msg)
                            logging.getLogger("voicetype.tray").error(msg)
                    return safe_handler

                action.triggered.connect(make_handler(callback))

            menu.addAction(action)

        return menu

    def set_icon(self, status: str):
        """Windows: no-op (icon update requires image files)."""
        pass

    def run(self):
        """啟動 Qt 事件循環"""
        self.start()
        from PyQt6.QtWidgets import QApplication
        import sys
        app = QApplication.instance()
        if app:
            sys.exit(app.exec())
        else:
            app = QApplication(sys.argv)
            self.start()
            sys.exit(app.exec())
