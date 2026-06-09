"""Application entry point."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow
from app.utils.font_loader import apply_font
from app.utils.rtl_utils import apply_app_rtl
from app.utils.theme import apply_dark_theme


def main() -> int:
    app = QApplication(sys.argv)

    apply_app_rtl(app)
    apply_font(app)
    apply_dark_theme(app)

    win = MainWindow()
    win.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
