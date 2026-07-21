"""
About VoiceType4TW-Mac dialog.
"""
import sys
from pathlib import Path
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QFont

class AboutDialog(QDialog):
    def __init__(self, is_dark=False):
        super().__init__()
        self.setWindowTitle("關於 VoiceType4TW")
        self.setFixedSize(360, 370)
        self._is_dark = is_dark
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        # Theme colors
        bg_color = "#1e1e1e" if self._is_dark else "#ffffff"
        text_color = "#e0e0e0" if self._is_dark else "#333333"
        self.setStyleSheet(f"background-color: {bg_color};")

        # Icon
        icon_label = QLabel()
        icon_path = Path(__file__).parent.parent / "assets" / "icon.png"
        if icon_path.exists():
            pixmap = QPixmap(str(icon_path))
            icon_label.setPixmap(pixmap.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        # App Name
        import platform
        font_family = "PingFang TC" if platform.system() == "Darwin" else "Microsoft JhengHei"
        name_label = QLabel("VoiceType4TW")
        name_label.setFont(QFont(font_family, 18, QFont.Weight.Bold))
        name_label.setStyleSheet(f"color: {text_color};")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name_label)

        # Version
        from paths import VERSION_NAME
        version_label = QLabel(f"Version {VERSION_NAME}")
        version_label.setStyleSheet("color: #888; font-size: 12px;")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)

        # Credits
        credit_box = QVBoxLayout()
        credit_box.setSpacing(5)
        
        dev_label = QLabel("主要開發者：吉米丘, CC58TW")
        dev_label.setStyleSheet(f"color: {text_color}; font-size: 13px;")
        dev_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        assist_label = QLabel("GitHub 協作者：JayC-TW, go-mask, chrisliuqq")
        assist_label.setStyleSheet(f"color: {text_color}; font-size: 13px;")
        assist_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        credit_box.addWidget(dev_label)
        credit_box.addWidget(assist_label)
        layout.addLayout(credit_box)

        layout.addStretch()

        # Close button
        btn_close = QPushButton("關閉")
        btn_close.setFixedWidth(80)
        btn_close.setStyleSheet("""
            QPushButton { 
                padding: 6px; border-radius: 4px; background: #007aff; color: white; 
                font-weight: bold; border: none;
            }
            QPushButton:hover { background: #0066cc; }
        """)
        btn_close.clicked.connect(self.accept)
        
        h_box = QHBoxLayout()
        h_box.addStretch()
        h_box.addWidget(btn_close)
        h_box.addStretch()
        layout.addLayout(h_box)

if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    dialog = AboutDialog(is_dark=True)
    dialog.show()
    sys.exit(app.exec())
