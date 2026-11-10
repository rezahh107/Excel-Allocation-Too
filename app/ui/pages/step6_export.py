"""Step 6 — export an approved Excel workbook with safety UX."""
from __future__ import annotations

from datetime import datetime
from tempfile import TemporaryDirectory
import os
from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWizardPage,
)

from app.core.models import WizardState
from app.services.excel_service import export_excel
from app.services.simulation_service import imbalance_report
from app.utils.helpers import open_in_explorer
from app.utils.rtl_utils import apply_rtl
from app.utils.theme import ColorPalette as P


class Step6Export(QWizardPage):
    """Export wizard page."""

    def __init__(self, state: WizardState) -> None:
        super().__init__()
        apply_rtl(self)
        self.state = state
        self.setTitle("مرحله ۶: خروجی و آمار")

        lay = QVBoxLayout(self)

        path_bar = QHBoxLayout()
        self.path = QLineEdit(self._default_export_path())
        browse = QPushButton("...")
        browse.setFixedWidth(36)
        browse.clicked.connect(self._browse)
        path_bar.addWidget(QLabel("مسیر فایل:"))
        path_bar.addWidget(self.path)
        path_bar.addWidget(browse)
        lay.addLayout(path_bar)

        btn_bar = QHBoxLayout()
        self.export_btn = QPushButton("💾  خروجی گرفتن (Ctrl+S)")
        self.export_btn.setObjectName("btn_primary")
        self.export_btn.clicked.connect(self.export)

        self.open_btn = QPushButton("📂  باز کردن پوشه")
        self.open_btn.setObjectName("btn_secondary")
        self.open_btn.setEnabled(False)
        self.open_btn.clicked.connect(
            lambda: open_in_explorer(self.path.text())
        )

        btn_bar.addWidget(self.export_btn)
        btn_bar.addWidget(self.open_btn)
        btn_bar.addStretch()
        lay.addLayout(btn_bar)

        stats_grp = QGroupBox("آمار نهایی")
        stats_lay = QVBoxLayout(stats_grp)

        self.summary = QLabel("")
        self.summary.setObjectName("lbl_muted")
        self.summary.setWordWrap(True)
        stats_lay.addWidget(self.summary)

        lay.addWidget(stats_grp)
        lay.addStretch()

    # ── QWizardPage API ─────────────────────────────────────────
    def initializePage(self) -> None:  # noqa: N802
        if not self.path.text().strip():
            self.path.setText(self._default_export_path())

        result = self.state.result
        if result:
            rep = imbalance_report(result)
            self.summary.setStyleSheet(f"color:{P.TEXT_MUTED}")
            self.summary.setText(
                "آماده خروجی گرفتن:\n"
                f"دانش‌آموزان: {result.total_students}  |  "
                f"پشتیبان‌ها: {result.total_mentors}  |  "
                f"ظرفیت: {rep['capacity']}  |  "
                f"حداقل: {rep['min']}  |  حداکثر: {rep['max']}  |  "
                f"میانگین: {rep['avg']}  |  "
                f"جابه‌جا شده: {result.num_moved}"
            )
        else:
            self.summary.setStyleSheet(f"color:{P.WARNING_LIGHT}")
            self.summary.setText("⚠ هنوز نتیجه‌ای برای خروجی وجود ندارد.")

    def isComplete(self) -> bool:  # noqa: N802
        return True

    # ── actions ─────────────────────────────────────────────────
    def _browse(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "ذخیره",
            self._default_export_path(),
            "Excel (*.xlsx)",
        )
        if path:
            self.path.setText(path)

    def export(self) -> None:
        """Write the approved Excel workbook to disk."""
        try:
            result = self.state.assert_current_result(require_approved=True)
        except Exception as exc:
            self.summary.setStyleSheet(f"color:{P.WARNING_LIGHT}")
            self.summary.setText(f"⚠ خروجی ممنوع: {exc}")
            return
        if not result:
            self.summary.setStyleSheet(f"color:{P.WARNING_LIGHT}")
            self.summary.setText("⚠ نتیجه‌ای برای خروجی وجود ندارد.")
            return

        out_path = self._normalize_output_path(self.path.text())
        self.path.setText(str(out_path))

        if out_path.exists():
            ans = QMessageBox.warning(
                self,
                "تأیید بازنویسی فایل",
                f"فایل زیر از قبل وجود دارد:\n{out_path}\n\n"
                "آیا مایل به بازنویسی آن هستید؟",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if ans != QMessageBox.StandardButton.Yes:
                self.summary.setStyleSheet(f"color:{P.WARNING_LIGHT}")
                self.summary.setText("⚠ عملیات خروجی توسط کاربر لغو شد.")
                return

        mentor_manager = {m.name: m.manager for m in result.mentors}

        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)

            with TemporaryDirectory(dir=out_path.parent) as tmp:
                excel_stage = Path(tmp) / "final.xlsx"
                export_excel(result, mentor_manager, str(excel_stage))
                # Recheck before publishing either output; no stale approval.
                if result is not self.state.assert_current_result(require_approved=True):
                    raise ValueError("نتیجه پس از تأیید تغییر کرده است.")
                os.replace(excel_stage, out_path)

        except Exception as exc:  # noqa: BLE001
            msg = f"خطا در خروجی: {exc}"
            self.summary.setStyleSheet(f"color:{P.ERROR_LIGHT}")
            self.summary.setText(f"❌ {msg}")
            if self.wizard() and hasattr(self.wizard(), "toast"):
                self.wizard().toast.show_message(msg, "error")
            return

        self.open_btn.setEnabled(True)
        self.summary.setStyleSheet(f"color:{P.SUCCESS_LIGHT}")
        self.summary.setText(
            f"✅ فایل اکسل ذخیره شد:\n{out_path}"
        )

        if self.wizard() and hasattr(self.wizard(), "toast"):
            self.wizard().toast.show_message(
                "خروجی با موفقیت ذخیره شد ✅",
                "success",
                4000,
            )

    # ── helpers ────────────────────────────────────────────────
    @staticmethod
    def _default_export_path() -> str:
        desktop = Path.home() / "Desktop"
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return str(desktop / f"final_assignment_{ts}.xlsx")

    @staticmethod
    def _normalize_output_path(raw: str) -> Path:
        text = (raw or "").strip()
        if not text:
            return Path(Step6Export._default_export_path())

        path = Path(text).expanduser()

        if path.suffix.lower() != ".xlsx":
            path = path.with_suffix(".xlsx")

        if not path.is_absolute():
            path = Path.cwd() / path

        return path
