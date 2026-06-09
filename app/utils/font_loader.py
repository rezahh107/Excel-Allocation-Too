"""Font loading — Vazirmatn (Persian) with Tahoma fallback."""
from __future__ import annotations
from pathlib import Path

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

from app.utils.logger import get_logger

log = get_logger("font_loader")

_FONT_DIR = Path(__file__).parent.parent.parent / "resources" / "fonts"
_VAZIR_FILES = [
    ("VazirMatn-Regular.ttf", "Vazirmatn"),
    ("VazirMatn-Bold.ttf",    "Vazirmatn"),
]


def load_fonts() -> str:
    """Load Vazirmatn if available; return the family name to use."""
    loaded = False
    for filename, _family in _VAZIR_FILES:
        fpath = _FONT_DIR / filename
        if fpath.exists():
            fid = QFontDatabase.addApplicationFont(str(fpath))
            if fid >= 0:
                loaded = True
                log.info("فونت بارگذاری شد: %s", filename)
            else:
                log.warning("بارگذاری فونت ناموفق: %s", filename)
        else:
            log.debug("فایل فونت یافت نشد: %s", fpath)
    if loaded:
        return "Vazirmatn"
    log.info("فونت Vazirmatn یافت نشد — Tahoma جایگزین شد.")
    return "Tahoma"


def apply_font(app: QApplication) -> None:
    """Load fonts and set the application-wide default family."""
    family = load_fonts()
    from PySide6.QtGui import QFont
    font = QFont(family, 11)
    app.setFont(font)
