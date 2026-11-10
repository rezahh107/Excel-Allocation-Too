"""Step 4 — drag & drop preview with undo/redo (B7, B8)."""
from __future__ import annotations
from PySide6.QtGui import QUndoStack
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QMessageBox,
                               QPushButton, QVBoxLayout, QWizardPage)

from app.core.models import WizardState
from app.services.allocation_service import allocate
from app.core.validation import validate_result
from app.ui.commands import ReassignCommand
from app.ui.widgets.allocation_tree import AllocationTree
from app.utils.rtl_utils import apply_rtl
from app.utils.theme import ColorPalette as P


class Step4Preview(QWizardPage):
    """Preview page: drag & drop reassignment + undo/redo."""

    def __init__(self, state: WizardState) -> None:
        super().__init__()
        apply_rtl(self)
        self.state      = state
        self.undo_stack = QUndoStack(self)
        self.setTitle("مرحله ۴: پیش‌نمایش و ویرایش دستی")
        self.setSubTitle(
            "دانش‌آموز را بکشید و روی پشتیبان دیگری رها کنید.")

        lay = QVBoxLayout(self)
        # undo/redo bar
        undo_bar = QHBoxLayout()
        self.undo_btn = QPushButton("↩  واگرد (Ctrl+Z)")
        self.redo_btn = QPushButton("↪  ازنو  (Ctrl+Y)")
        self.undo_btn.setObjectName("btn_secondary")
        self.redo_btn.setObjectName("btn_secondary")
        self.undo_btn.clicked.connect(self.undo_stack.undo)
        self.redo_btn.clicked.connect(self.undo_stack.redo)
        undo_bar.addWidget(self.undo_btn)
        undo_bar.addWidget(self.redo_btn)
        undo_bar.addStretch()
        lay.addLayout(undo_bar)

        # count label (B8)
        self.count_lbl = QLabel("")
        self.count_lbl.setObjectName("lbl_muted")
        lay.addWidget(self.count_lbl)

        # feedback label (B7)
        self.info = QLabel(
            "یک دانش‌آموز را بکشید و روی پشتیبان دیگری رها کنید.")
        self.info.setObjectName("lbl_muted")
        self.info.setWordWrap(True)
        lay.addWidget(self.info)

        # tree
        self.tree = AllocationTree()
        self.tree.moveRequested.connect(self._on_move)
        lay.addWidget(self.tree)

        self.load_more_btn = QPushButton("نمایش بیشتر")
        self.load_more_btn.setObjectName("btn_secondary")
        self.load_more_btn.clicked.connect(self._load_more)
        lay.addWidget(self.load_more_btn)

        self.undo_stack.indexChanged.connect(self._update_buttons)

    # ── QWizardPage API ─────────────────────────────────────────
    def initializePage(self) -> None:  # noqa: N802
        self.state.preview_reviewed = False
        self._preview_error = ""
        try:
            if (self.state.result is None or
                    self.state.result_input_signature != self.state.input_signature()):
                self.state.invalidate_result()
                self.state.result = allocate(self.state)
                self.state.result_input_signature = self.state.input_signature()
            self.state.result.approved_assignment_snapshot = None
            self.undo_stack.clear()
            self.tree.load(self.state.result)
            self.info.setText("پیش‌نمایش حاضر است؛ تخصیص‌های دستی باید همچنان متعادل بمانند.")
        except Exception as exc:
            self._preview_error = str(exc)
            self.info.setText("❌ " + self._preview_error)
        self._update_count_label()
        self._update_buttons()
        self.completeChanged.emit()

    def validatePage(self) -> bool:  # noqa: N802
        try:
            result = self.state.assert_current_result()
            if self._preview_error:
                raise ValueError(self._preview_error)
            issues = validate_result(result)
            if issues:
                raise ValueError(" | ".join(issues))
        except Exception as exc:
            self.state.preview_reviewed = False
            QMessageBox.warning(self, "تخصیص نامعتبر", str(exc))
            return False
        self.state.preview_reviewed = True
        return True

    def isComplete(self) -> bool:  # noqa: N802
        return not getattr(self, "_preview_error", "") and self.state.result is not None

    # ── drop handler ────────────────────────────────────────────
    def _on_move(self, student_idx: int,
                 old_mentor: str, new_mentor: str) -> None:
        result = self.state.result
        if result is None:
            return
        self.state.preview_reviewed = False
        result.approved_assignment_snapshot = None
        # validation: stabilised
        if student_idx in result.stabilized:
            self._error("🔒 دانش‌آموز تثبیت‌شده قابل جابه‌جایی نیست.")
            return
        # validation: capacity
        if len(result.assigned.get(new_mentor, [])) >= result.capacity:
            self._error(
                f"🔴 ظرفیت پشتیبان «{new_mentor}» تکمیل است. "
                "انتقال لغو شد.")
            return
        cmd = ReassignCommand(
            result, student_idx, old_mentor, new_mentor,
            self._on_cmd_applied)
        self.undo_stack.push(cmd)
        # B7 — descriptive feedback
        stu = result.students[student_idx]
        name = f"{stu.first} {stu.last}".strip() or stu.counter
        self.info.setText(
            f"✅  {name}  از  «{old_mentor}»  به  «{new_mentor}»  "
            "منتقل شد.")
        self.info.setStyleSheet(f"color:{P.SUCCESS_LIGHT}")

    def _on_cmd_applied(self) -> None:
        self.tree.reload()
        self._update_count_label()
        if self.wizard():
            self.wizard().refresh_status()

    def _error(self, msg: str) -> None:
        self.info.setText(msg)
        self.info.setStyleSheet(f"color:{P.ERROR_LIGHT}")
        self.tree.reload()

    def _load_more(self) -> None:
        """Show next page of students in the allocation tree."""
        self.tree.show_more()
        self._update_count_label()

    def _update_buttons(self) -> None:
        self.undo_btn.setEnabled(self.undo_stack.canUndo())
        self.redo_btn.setEnabled(self.undo_stack.canRedo())

    def _update_count_label(self) -> None:
        """Show accurate visible/total student count."""
        result = self.state.result
        if result is None:
            self.count_lbl.setText("")
            if hasattr(self, "load_more_btn"):
                self.load_more_btn.setEnabled(False)
            return

        showing = self.tree.visible_students_count()
        total = self.tree.total_students_count()

        self.count_lbl.setText(
            f"نمایش {showing} از {total} دانش‌آموز"
        )

        if hasattr(self, "load_more_btn"):
            can_more = self.tree.can_show_more()
            self.load_more_btn.setEnabled(can_more)
            self.load_more_btn.setVisible(can_more)
