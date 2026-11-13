"""Confirmation dialog shown before approving the reviewed allocation.

The dialog is intentionally defensive: it can summarize either an already
simulated AllocationResult from Step4 or raw students/mentors built right
before Step5 execution.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app.core.models import WizardState
from app.utils.rtl_utils import apply_rtl
from app.utils.theme import ColorPalette as P


@dataclass(frozen=True)
class _ExecutionSummary:
    students: int
    mentors: int
    fairness: str
    capacity: int
    max_load: int
    min_load: int
    imbalance: int
    full_or_over: int
    warnings: list[str]


class ConfirmExecutionDialog(QDialog):
    """Final confirmation dialog for the existing Step4 allocation."""

    def __init__(
        self,
        parent: QWidget | None,
        state: WizardState,
        students: list[Any],
        mentors: list[Any],
    ) -> None:
        super().__init__(parent)
        apply_rtl(self)

        self.setWindowTitle("تأیید نتیجه تخصیص")
        self.setModal(True)
        self.setMinimumWidth(520)

        summary = self._build_summary(state, students, mentors)

        lay = QVBoxLayout(self)
        lay.setSpacing(10)

        title = QLabel("آیا تخصیص بررسی‌شده زیر را تأیید می‌کنید؟")
        title.setObjectName("dialog_title")
        title.setWordWrap(True)
        title.setStyleSheet(
            f"color:{P.TEXT_PRIMARY};"
            "font-size:15px;"
            "font-weight:600;"
        )
        lay.addWidget(title)

        subtitle = QLabel(
            "تخصیص در مرحله پیش‌نمایش محاسبه شده است. "
            "این تأیید، مجوز خروجی Excel همان نتیجه خواهد بود."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color:{P.TEXT_MUTED};")
        lay.addWidget(subtitle)

        card = QFrame()
        card.setObjectName("confirm_card")
        card.setStyleSheet(
            f"QFrame#confirm_card{{"
            f"background:{P.BG_SURFACE};"
            f"border:1px solid {P.BORDER};"
            "border-radius:10px;"
            "padding:8px;"
            "}}"
        )
        grid = QGridLayout(card)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)

        rows = [
            ("تعداد دانش‌آموزان", str(summary.students)),
            ("تعداد پشتیبان‌ها", str(summary.mentors)),
            ("روش عدالت", summary.fairness),
            ("ظرفیت", str(summary.capacity)),
            ("بیشترین بار", str(summary.max_load)),
            ("کمترین بار", str(summary.min_load)),
            ("اختلاف بار", str(summary.imbalance)),
            ("پشتیبان‌های پر/بالاتر از ظرفیت", str(summary.full_or_over)),
        ]

        for row, (key, value) in enumerate(rows):
            k = QLabel(key)
            v = QLabel(value)
            k.setStyleSheet(f"color:{P.TEXT_MUTED};")
            v.setStyleSheet(
                f"color:{P.TEXT_PRIMARY};"
                "font-weight:600;"
            )
            k.setAlignment(Qt.AlignmentFlag.AlignRight)
            v.setAlignment(Qt.AlignmentFlag.AlignLeft)
            grid.addWidget(k, row, 0)
            grid.addWidget(v, row, 1)

        lay.addWidget(card)

        if summary.warnings:
            warn = QLabel("⚠ " + "\n⚠ ".join(summary.warnings))
            warn.setWordWrap(True)
            warn.setStyleSheet(
                f"color:{P.WARNING_LIGHT};"
                f"background:{P.BG_SURFACE};"
                f"border:1px solid {P.WARNING};"
                "border-radius:8px;"
                "padding:8px;"
            )
            lay.addWidget(warn)
        else:
            ok = QLabel("✅ وضعیت اولیه برای اجرا مناسب به نظر می‌رسد.")
            ok.setWordWrap(True)
            ok.setStyleSheet(
                f"color:{P.SUCCESS_LIGHT};"
                f"background:{P.BG_SURFACE};"
                f"border:1px solid {P.SUCCESS};"
                "border-radius:8px;"
                "padding:8px;"
            )
            lay.addWidget(ok)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(
            "تأیید نتیجه"
        )
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(
            "لغو"
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

    @classmethod
    def confirm(
        cls,
        parent: QWidget | None,
        state: WizardState,
        students: list[Any],
        mentors: list[Any],
    ) -> bool:
        """Return True if user confirms execution."""
        dlg = cls(parent, state, students, mentors)
        return dlg.exec() == QDialog.DialogCode.Accepted

    @staticmethod
    def _build_summary(
        state: WizardState,
        students: list[Any],
        mentors: list[Any],
    ) -> _ExecutionSummary:
        result = getattr(state, "result", None)

        loads: dict[str, int] = {}
        capacity = int(getattr(result, "capacity", 0) or 0)

        if result is not None and hasattr(result, "load_per_mentor"):
            try:
                loads = dict(result.load_per_mentor())
            except Exception:  # noqa: BLE001
                loads = {}

        if not loads and result is not None:
            assigned = getattr(result, "assigned", {}) or {}
            try:
                loads = {
                    str(name): len(items)
                    for name, items in assigned.items()
                }
            except Exception:  # noqa: BLE001
                loads = {}

        if not capacity:
            capacity = int(getattr(state, "capacity", 0) or 0)

        if not capacity and mentors:
            # Conservative estimate used only for UI warning.
            capacity = max(1, -(-len(students) // max(1, len(mentors))))

        if not loads:
            # Before actual run we may not have a fresh result; show a neutral
            # estimated distribution so the dialog stays useful.
            loads = {
                str(getattr(m, "name", f"پشتیبان {i + 1}")): 0
                for i, m in enumerate(mentors)
            }

        vals = list(loads.values())
        max_load = max(vals) if vals else 0
        min_load = min(vals) if vals else 0
        imbalance = max_load - min_load if vals else 0
        full_or_over = len([
            value for value in vals
            if capacity and value >= capacity
        ])

        fairness_obj = getattr(state, "fairness", "")
        fairness = getattr(fairness_obj, "value", str(fairness_obj))

        warnings: list[str] = []
        if not students:
            warnings.append("هیچ دانش‌آموزی برای تخصیص یافت نشد.")
        if not mentors:
            warnings.append("هیچ پشتیبانی برای تخصیص یافت نشد.")
        if capacity and full_or_over:
            warnings.append(
                f"{full_or_over} پشتیبان در وضعیت ظرفیت کامل یا بالاتر هستند."
            )
        if capacity and max_load > capacity:
            warnings.append(
                "برخی پشتیبان‌ها از ظرفیت تعریف‌شده عبور کرده‌اند."
            )
        if imbalance > 2:
            warnings.append(
                f"اختلاف بار بین پشتیبان‌ها نسبتاً زیاد است: {imbalance}"
            )

        return _ExecutionSummary(
            students=len(students),
            mentors=len(mentors),
            fairness=fairness,
            capacity=capacity,
            max_load=max_load,
            min_load=min_load,
            imbalance=imbalance,
            full_or_over=full_or_over,
            warnings=warnings,
        )
