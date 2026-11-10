"""Step 5 — execute allocation with stage indicator (B9)."""
from __future__ import annotations
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QProgressBar,
                               QPushButton, QVBoxLayout, QWizardPage)

from app.core.models import WizardState
from app.core.validation import validate_result
from app.ui.widgets.confirm_execution_dialog import ConfirmExecutionDialog
from app.ui.widgets.log_viewer import LogViewer
from app.ui.widgets.stage_indicator import StageIndicator
from app.utils.rtl_utils import apply_rtl
from app.utils.theme import ColorPalette as P


class _Worker(QThread):
    progress = Signal(int, str, str)
    finished_ok = Signal(object)
    failed = Signal(str)

    def __init__(self, result) -> None:
        super().__init__()
        self._result = result
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        try:
            self.progress.emit(25, "بررسی پیش‌نمایش...", "load")
            if self._stop:
                raise RuntimeError("اجرا توسط کاربر متوقف شد.")
            self.progress.emit(85, "اعتبارسنجی تخصیص...", "validate")
            issues = validate_result(self._result)
            if issues:
                self.failed.emit(" | ".join(issues))
                return
            if self._stop:
                raise RuntimeError("اجرا توسط کاربر متوقف شد.")
            self.progress.emit(100, "تأیید تخصیص بررسی‌شده", "done")
            self.finished_ok.emit(self._result)
        except Exception as exc:
            self.failed.emit(str(exc))


class Step5Execute(QWizardPage):
    """Execution wizard page with stage indicator."""

    def __init__(self, state: WizardState) -> None:
        super().__init__()
        apply_rtl(self)
        self.state   = state
        self._worker: _Worker | None = None
        self._done   = False
        self._running = False
        self.setTitle("مرحله ۵: اجرای تخصیص")

        lay = QVBoxLayout(self)
        self.stage = StageIndicator()
        lay.addWidget(self.stage)
        self.pbar = QProgressBar()
        self.pbar.setTextVisible(True)
        lay.addWidget(self.pbar)
        btn_bar = QHBoxLayout()
        self.run_btn  = QPushButton("▶  اجرا")
        self.stop_btn = QPushButton("⏹  توقف")
        self.run_btn.setObjectName("btn_primary")
        self.stop_btn.setObjectName("btn_danger")
        self.stop_btn.setEnabled(False)
        self.run_btn.clicked.connect(self.start)
        self.stop_btn.clicked.connect(self.stop)
        btn_bar.addWidget(self.run_btn)
        btn_bar.addWidget(self.stop_btn)
        btn_bar.addStretch()
        lay.addLayout(btn_bar)
        self.log = LogViewer()
        lay.addWidget(self.log)

    # ── QWizardPage API ─────────────────────────────────────────
    def initializePage(self) -> None:  # noqa: N802
        self._done = False
        self._running = False
        self.stage.reset()
        self.pbar.setValue(0)
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.start()

    def isComplete(self) -> bool:  # noqa: N802
        return self._done

    # ── execution ────────────────────────────────────────────────
    def start(self) -> None:
        if self._running:
            return

        try:
            result = self.state.assert_current_result()
            if not self.state.preview_reviewed:
                raise ValueError("ابتدا پیش‌نمایش را در مرحله ۴ بررسی و تأیید کنید.")
        except Exception as exc:
            self._done = False
            self.log.add("ERROR", str(exc))
            self.completeChanged.emit()
            return

        if not ConfirmExecutionDialog.confirm(
            self, self.state, result.students, result.mentors
        ):
            self.log.add("WARNING", "اجرای تخصیص توسط کاربر لغو شد.")
            return

        self.stage.reset()
        self.log.add("INFO", "تأیید همان تخصیص مشاهده‌شده...")
        self._running = True
        self._done = False
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self._worker = _Worker(result)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_ok.connect(self._on_ok)
        self._worker.failed.connect(self._on_fail)
        self._worker.start()

    def stop(self) -> None:
        if self._worker:
            self._worker.stop()
            self.log.add("WARNING", "درخواست توقف ارسال شد.")

    # ── worker callbacks ─────────────────────────────────────────
    def _on_progress(self, p: int, msg: str, stage_key: str) -> None:
        self.pbar.setValue(p)
        self.log.add("INFO", msg)
        self.stage.set_stage(stage_key, "running")
        if p >= 100:
            self.stage.set_stage(stage_key, "done")

    def _on_ok(self, result) -> None:
        self._running = False
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        try:
            if result is not self.state.assert_current_result():
                raise ValueError("نتیجه پس از پیش‌نمایش تغییر کرده است.")
            if not self.state.preview_reviewed:
                raise ValueError("پیش‌نمایش دوباره باید تأیید شود.")
            result.mark_approved()
        except Exception as exc:
            self._on_fail(str(exc))
            return
        self._done = True
        self.stage.set_stage("done", "done")
        self.log.add("INFO", "✅ تخصیص با موفقیت انجام شد.")
        self.completeChanged.emit()
        if self.wizard():
            self.wizard().refresh_status()
            self.wizard().next()

    def _on_fail(self, msg: str) -> None:
        self._running = False
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.log.add("ERROR", f"❌ {msg}")
        for key in ("load", "domain", "allocate", "validate", "done"):
            self.stage.set_stage(key, "error")
        if self.wizard() and hasattr(self.wizard(), "toast"):
            self.wizard().toast.show_message(f"خطا: {msg}", "error")
