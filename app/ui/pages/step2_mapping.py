"""Step 2 — column mapping with live preview (B3) and inline errors (B2)."""
from __future__ import annotations
from PySide6.QtWidgets import (QGroupBox, QHBoxLayout, QHeaderView, QLabel,
                               QPushButton, QScrollArea, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget,
                               QWizardPage)

from app.core.models import (OPTIONAL_BOOK1, OPTIONAL_BOOK2,
                              REQUIRED_BOOK1, REQUIRED_BOOK2,
                              Role, WizardState)
from app.core.validation import validate_mapping
from app.services.mapping_service import auto_detect
from app.ui.widgets.mapping_table import MappingTable
from app.utils.rtl_utils import apply_rtl

_ROLES1 = REQUIRED_BOOK1 | OPTIONAL_BOOK1
_ROLES2 = REQUIRED_BOOK2 | OPTIONAL_BOOK2


class Step2Mapping(QWizardPage):
    """Column mapping wizard page."""

    def __init__(self, state: WizardState) -> None:
        super().__init__()
        apply_rtl(self)
        self.state = state
        self.setTitle("مرحله ۲: نگاشت ستون‌ها")
        self.setSubTitle(
            "ستون‌های الزامی را به نقش صحیح نگاشت دهید.")

        # ── scroll wrapper ────────────────────────────────────
        inner = QWidget()
        apply_rtl(inner)
        inner_lay = QVBoxLayout(inner)

        # book1 mapping
        grp1 = QGroupBox("Book1 — پشتیبان‌ها")
        g1lay = QVBoxLayout(grp1)
        self.table1 = MappingTable(required=REQUIRED_BOOK1)
        g1lay.addWidget(self.table1)
        inner_lay.addWidget(grp1)

        # book2 mapping
        grp2 = QGroupBox("Book2 — دانش‌آموزان")
        g2lay = QVBoxLayout(grp2)
        self.table2 = MappingTable(required=REQUIRED_BOOK2)
        g2lay.addWidget(self.table2)
        inner_lay.addWidget(grp2)

        # auto-fix button
        bar = QHBoxLayout()
        fix = QPushButton("🔧  رفع خودکار خطاها")
        fix.setObjectName("btn_secondary")
        fix.clicked.connect(self.auto_fix)
        bar.addWidget(fix)
        bar.addStretch()
        inner_lay.addLayout(bar)

        # live preview (B3)
        self._preview_group = QGroupBox("پیش‌نمایش داده (۳ ردیف اول)")
        pv_lay = QVBoxLayout(self._preview_group)
        self._preview_table = QTableWidget(0, 1)
        self._preview_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self._preview_table.setFixedHeight(130)
        pv_lay.addWidget(self._preview_table)
        inner_lay.addWidget(self._preview_group)
        inner_lay.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(inner)
        outer = QVBoxLayout(self)
        outer.addWidget(scroll)

        for t in (self.table1, self.table2):
            t.mappingChanged.connect(self._on_mapping_changed)

    # ── QWizardPage API ─────────────────────────────────────────
    def initializePage(self) -> None:  # noqa: N802
        m1 = auto_detect(self.state.book1_headers, _ROLES1)
        m2 = auto_detect(self.state.book2_headers, _ROLES2)
        m1 = self._apply_saved(m1, self.state.map1 or self.state.saved_map1)
        m2 = self._apply_saved(m2, self.state.map2 or self.state.saved_map2)
        self.table1.load(m1)
        self.table2.load(m2)
        self._validate()

    def isComplete(self) -> bool:  # noqa: N802
        return not self.state.map_errors

    def incomplete_reason(self) -> str:
        return "ابتدا خطاهای نگاشت ستون‌ها را برطرف کنید."

    # ── slots ────────────────────────────────────────────────────
    def auto_fix(self) -> None:
        self.table1.load(auto_detect(self.state.book1_headers, _ROLES1))
        self.table2.load(auto_detect(self.state.book2_headers, _ROLES2))
        self._validate()

    def _on_mapping_changed(self) -> None:
        self._validate()
        self._update_preview()

    def _validate(self) -> None:
        new_map1 = self.table1.current_mapping()
        new_map2 = self.table2.current_mapping()
        if new_map1 != self.state.map1 or new_map2 != self.state.map2:
            self.state.invalidate_result()
        self.state.map1 = new_map1
        self.state.map2 = new_map2
        errs1 = validate_mapping(self.state.map1, REQUIRED_BOOK1)
        errs2 = validate_mapping(self.state.map2, REQUIRED_BOOK2)
        self.state.map_errors = errs1 + errs2
        self.table1.set_inline_error(errs1)
        self.table2.set_inline_error(errs2)
        self.completeChanged.emit()
        if self.wizard():
            self.wizard().refresh_status()

    # ── live preview (B3) ────────────────────────────────────────
    def _update_preview(self) -> None:
        """Show first 3 rows of book2 using current mapping."""
        inv2 = {role: col for col, role in self.state.map2.items()
                if role != Role.NONE}
        if not inv2 or not self.state.book2_rows:
            self._preview_table.setRowCount(0)
            return
        role_order = [r for r in Role if r in inv2 and r != Role.NONE]
        headers = [r.value for r in role_order]
        self._preview_table.setColumnCount(len(headers))
        self._preview_table.setHorizontalHeaderLabels(headers)
        rows = self.state.book2_rows[:3]
        self._preview_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, role in enumerate(role_order):
                col_name = inv2.get(role, "")
                val = row.get(col_name, "—")
                item = QTableWidgetItem(val)
                self._preview_table.setItem(r, c, item)

    # ── helpers ──────────────────────────────────────────────────
    @staticmethod
    def _apply_saved(detected: dict[str, Role],
                     saved: dict[str, str]) -> dict[str, Role]:
        out = dict(detected)
        for col, rv in saved.items():
            if col in out:
                try:
                    out[col] = rv if isinstance(rv, Role) else Role(rv)
                except ValueError:
                    pass
        return out
