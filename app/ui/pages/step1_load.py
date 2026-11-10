"""Step 1 — load Book1 and Book2 files."""
from __future__ import annotations
from pathlib import Path

from PySide6.QtWidgets import (QHBoxLayout, QLabel, QVBoxLayout,
                               QWizardPage)

from app.core.models import WizardState
from app.services.excel_service import load_table
from app.ui.widgets.file_drop_zone import FileDropZone
from app.utils.rtl_utils import apply_rtl


class Step1Load(QWizardPage):
    """File loading wizard page with drag-and-drop zones."""

    def __init__(self, state: WizardState) -> None:
        super().__init__()
        apply_rtl(self)
        self.state = state
        self.setTitle("مرحله ۱: بارگذاری فایل‌ها")
        self.setSubTitle("فایل‌های Excel یا CSV خود را بکشید و رها کنید.")
        lay = QVBoxLayout(self)
        zones = QHBoxLayout()
        self.zone1 = FileDropZone("📋  Book1  (پشتیبان‌ها)")
        self.zone2 = FileDropZone("📋  Book2  (دانش‌آموزان)")
        self.zone1.fileSelected.connect(lambda p: self.load_file(1, p))
        self.zone2.fileSelected.connect(lambda p: self.load_file(2, p))
        zones.addWidget(self.zone1)
        zones.addWidget(self.zone2)
        lay.addLayout(zones)
        self.status = QLabel("")
        self.status.setObjectName("lbl_muted")
        self.status.setWordWrap(True)
        lay.addWidget(self.status)

    # ── public ──────────────────────────────────────────────────
    def load_file(self, which: int, path: str) -> None:
        """Load a CSV/XLSX into shared state and refresh UI."""
        if not path or not Path(path).exists():
            return
        try:
            headers, rows = load_table(path)
        except Exception as exc:  # noqa: BLE001
            zone = self.zone1 if which == 1 else self.zone2
            zone.set_status(f"❌ خطا: {exc}")
            self._notify_toast("error", f"خطا در بارگذاری: {exc}")
            return
        self.state.invalidate_result()
        zone = self.zone1 if which == 1 else self.zone2
        if which == 1:
            self.state.book1_path    = path
            self.state.book1_headers = headers
            self.state.book1_rows    = rows
        else:
            self.state.book2_path    = path
            self.state.book2_headers = headers
            self.state.book2_rows    = rows
        name = Path(path).name
        zone.set_status(f"✅  {name}  —  {len(rows)} ردیف")
        self._notify_toast("success", f"{name} با موفقیت بارگذاری شد.")
        self.completeChanged.emit()
        if self.wizard():
            self.wizard().refresh_status()

    def restore_paths(self) -> None:
        """Auto-reload previously used files if they still exist."""
        if self.state.book1_path and Path(self.state.book1_path).exists():
            self.load_file(1, self.state.book1_path)
        if self.state.book2_path and Path(self.state.book2_path).exists():
            self.load_file(2, self.state.book2_path)

    # ── QWizardPage API ─────────────────────────────────────────
    def isComplete(self) -> bool:  # noqa: N802
        ok = bool(self.state.book1_rows) and bool(self.state.book2_rows)
        if not ok:
            self.status.setText(
                "⚠  هر دو فایل Book1 و Book2 باید بارگذاری شوند.")
            self.status.setStyleSheet("color:#ef5350")
        else:
            self.status.setText(
                f"✅  Book1: {len(self.state.book1_rows)} ردیف"
                f"  |  Book2: {len(self.state.book2_rows)} ردیف")
            self.status.setStyleSheet("color:#4caf50")
        return ok

    def incomplete_reason(self) -> str:
        return "هر دو فایل Book1 و Book2 باید بارگذاری شوند."

    # ── helper ──────────────────────────────────────────────────
    def _notify_toast(self, kind: str, msg: str) -> None:
        wiz = self.wizard()
        if wiz and hasattr(wiz, "toast"):
            wiz.toast.show_message(msg, kind)
