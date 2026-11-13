"""Step 5 — explicit confirmation of the already reviewed allocation (Method B)."""
from __future__ import annotations

from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWizardPage

from app.core.models import WizardState
from app.ui.widgets.confirm_execution_dialog import ConfirmExecutionDialog
from app.utils.rtl_utils import apply_rtl
from app.utils.theme import ColorPalette as P


class Step5Execute(QWizardPage):
    """Confirm the current allocation without a worker or simulated execution."""

    def __init__(self, state: WizardState) -> None:
        super().__init__()
        apply_rtl(self)
        self.state = state
        self._done = False
        self._confirming = False
        self.setTitle("مرحله ۵: تأیید تخصیص")
        self.setSubTitle("نتیجه مرحله ۴ را بررسی و به‌صورت صریح تأیید کنید.")

        layout = QVBoxLayout(self)
        self.message = QLabel("برای تأیید تخصیص بررسی‌شده، دکمه زیر را انتخاب کنید.")
        self.message.setObjectName("lbl_muted")
        self.message.setWordWrap(True)
        layout.addWidget(self.message)

        self.run_btn = QPushButton("✔ تأیید تخصیص")
        self.run_btn.setObjectName("btn_primary")
        self.run_btn.clicked.connect(self.start)
        layout.addWidget(self.run_btn)
        layout.addStretch()

    def initializePage(self) -> None:  # noqa: N802
        # Merely navigating must never open a modal or approve.
        self._done = self.state.export_eligible()
        self.message.setText(
            "تخصیص فعلی تأییدشده و آماده خروجی است." if self._done
            else "برای ادامه، ابتدا پیش‌نمایش را بررسی و سپس تأیید کنید."
        )
        self.completeChanged.emit()

    def isComplete(self) -> bool:  # noqa: N802
        return self._done and self.state.export_eligible()

    def validatePage(self) -> bool:  # noqa: N802
        # Programmatic wizard.next() must not bypass confirmation.
        return self.isComplete()

    def start(self) -> None:
        if self._confirming:
            return
        try:
            result = self.state.assert_current_result()
            if not self.state.preview_reviewed:
                raise ValueError("ابتدا پیش‌نمایش را در مرحله ۴ بررسی و تأیید کنید.")
        except Exception as exc:
            self._done = False
            self.message.setText(f"⚠ {exc}")
            self.message.setStyleSheet(f"color:{P.WARNING_LIGHT}")
            self.completeChanged.emit()
            return

        self._confirming = True
        try:
            confirmed = ConfirmExecutionDialog.confirm(
                self, self.state, result.students, result.mentors
            )
        finally:
            self._confirming = False
        if not confirmed:
            self.message.setText("تأیید لغو شد؛ هیچ تغییری ثبت نشد.")
            self.completeChanged.emit()
            return

        try:
            if result is not self.state.assert_current_result():
                raise ValueError("نتیجه در زمان تأیید تغییر کرده است.")
            if not self.state.preview_reviewed:
                raise ValueError("پیش‌نمایش دوباره باید بررسی شود.")
            result.mark_approved()
        except Exception as exc:
            self._done = False
            self.message.setText(f"⚠ تأیید انجام نشد: {exc}")
            self.message.setStyleSheet(f"color:{P.WARNING_LIGHT}")
            self.completeChanged.emit()
            return

        self._done = True
        self.message.setText("تخصیص فعلی با موفقیت تأیید شد.")
        self.message.setStyleSheet(f"color:{P.SUCCESS_LIGHT}")
        self.completeChanged.emit()
        wizard = self.wizard()
        if wizard:
            wizard.refresh_status()
            wizard.next()
