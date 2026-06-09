"""Editable column-mapping table with precise colour-coded validation.

MappingTable is used in Step2 to let the user map Excel columns to domain
roles. The widget intentionally keeps the public API small:

    load(mapping)
    current_mapping()
    set_inline_error(errors)

Signals:
    mappingChanged

UX rules:
    - required role selected      → green
    - optional role selected      → neutral/blue
    - unmapped column             → muted neutral
    - required roles missing      → summary warning, not every NONE row red
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.models import Role
from app.utils.theme import ColorPalette as P


class MappingTable(QWidget):
    """Three-column table: original | detected | override dropdown."""

    mappingChanged = Signal()

    def __init__(self, required: set[Role] | None = None) -> None:
        super().__init__()
        self._required: set[Role] = required or set()
        self._combos: dict[str, QComboBox] = {}

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        self.status_lbl = QLabel("")
        self.status_lbl.setObjectName("mapping_status")
        self.status_lbl.setWordWrap(True)
        self.status_lbl.setStyleSheet(
            f"color:{P.TEXT_SECONDARY};"
            f"background:{P.BG_SURFACE};"
            f"border:1px solid {P.BORDER};"
            "border-radius:6px;"
            "padding:5px 8px;"
        )
        lay.addWidget(self.status_lbl)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(
            ["ستون اصلی", "نقش تشخیص‌داده‌شده", "تغییر دستی"]
        )
        self.table.setAlternatingRowColors(False)
        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )
        self.table.verticalHeader().setVisible(False)

        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.table)

        self.error_lbl = QLabel("")
        self.error_lbl.setObjectName("lbl_error")
        self.error_lbl.setWordWrap(True)
        self.error_lbl.setStyleSheet(
            f"color:{P.ERROR_LIGHT};"
            f"background:{P.BG_SURFACE};"
            f"border:1px solid {P.ERROR};"
            "border-radius:6px;"
            "padding:5px 8px;"
        )
        self.error_lbl.hide()
        lay.addWidget(self.error_lbl)

    # ── Public API ────────────────────────────────────────────────
    def load(self, mapping: dict[str, Role]) -> None:
        """Populate the table from a mapping dict."""
        self.table.setRowCount(0)
        self._combos.clear()

        for col, role in mapping.items():
            row = self.table.rowCount()
            self.table.insertRow(row)

            item0 = self._readonly_item(col)
            self.table.setItem(row, 0, item0)

            item1 = self._readonly_item(role.value)
            self.table.setItem(row, 1, item1)

            combo = QComboBox()
            for rl in Role:
                combo.addItem(rl.value, rl)

            idx = combo.findData(role)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            else:
                combo.setCurrentText(role.value)

            combo.currentIndexChanged.connect(self._on_combo_changed)
            self._combos[col] = combo
            self.table.setCellWidget(row, 2, combo)

        self._recolour()

    def current_mapping(self) -> dict[str, Role]:
        """Return current column → role mapping."""
        return {
            col: cb.currentData()
            for col, cb in self._combos.items()
        }

    def set_inline_error(self, errors: list[str]) -> None:
        """Display inline validation errors below the table."""
        if errors:
            self.error_lbl.setText("⚠ " + "  |  ".join(errors))
            self.error_lbl.show()
        else:
            self.error_lbl.clear()
            self.error_lbl.hide()

        # Validation errors may change the user's mental model; refresh
        # status/tooltip colours after external validation as well.
        self._recolour()

    # ── Slots ─────────────────────────────────────────────────────
    def _on_combo_changed(self) -> None:
        self._recolour()
        self.mappingChanged.emit()

    # ── Rendering ─────────────────────────────────────────────────
    def _recolour(self) -> None:
        """Colour each row based on selected role and required coverage."""
        current = self.current_mapping()
        selected_roles = {
            role
            for role in current.values()
            if role is not None and role != Role.NONE
        }
        missing_required = self._required - selected_roles

        self._update_status_label(selected_roles, missing_required)

        for row in range(self.table.rowCount()):
            col_name = self.table.item(row, 0).text()
            role = current.get(col_name, Role.NONE)

            bg, fg, tooltip, combo_style = self._style_for_role(
                role=role,
                missing_required=missing_required,
            )

            for col in range(2):
                item = self.table.item(row, col)
                if item:
                    item.setBackground(bg)
                    item.setForeground(fg)
                    item.setToolTip(tooltip)

            combo = self._combos.get(col_name)
            if combo:
                combo.setToolTip(tooltip)
                combo.setStyleSheet(combo_style)

    def _update_status_label(
        self,
        selected_roles: set[Role],
        missing_required: set[Role],
    ) -> None:
        total = len(self._required)
        done = total - len(missing_required)

        if total == 0:
            self.status_lbl.setText("ستون الزامی تعریف نشده است.")
            self.status_lbl.setStyleSheet(
                f"color:{P.TEXT_SECONDARY};"
                f"background:{P.BG_SURFACE};"
                f"border:1px solid {P.BORDER};"
                "border-radius:6px;"
                "padding:5px 8px;"
            )
            return

        if missing_required:
            missing_names = "، ".join(
                role.value for role in sorted(
                    missing_required,
                    key=lambda r: r.value,
                )
            )
            self.status_lbl.setText(
                f"وضعیت نگاشت: {done}/{total} ستون الزامی تکمیل شده. "
                f"موارد ناقص: {missing_names}"
            )
            self.status_lbl.setStyleSheet(
                f"color:{P.WARNING_LIGHT};"
                f"background:{P.BG_SURFACE};"
                f"border:1px solid {P.WARNING};"
                "border-radius:6px;"
                "padding:5px 8px;"
            )
        else:
            optional_count = len([
                r for r in selected_roles if r not in self._required
            ])
            self.status_lbl.setText(
                f"وضعیت نگاشت: همه ستون‌های الزامی تکمیل شده‌اند "
                f"({done}/{total}). نقش‌های اختیاری انتخاب‌شده: "
                f"{optional_count}"
            )
            self.status_lbl.setStyleSheet(
                f"color:{P.SUCCESS_LIGHT};"
                f"background:{P.BG_SURFACE};"
                f"border:1px solid {P.SUCCESS};"
                "border-radius:6px;"
                "padding:5px 8px;"
            )

    def _style_for_role(
        self,
        role: Role,
        missing_required: set[Role],
    ) -> tuple[QColor, QColor, str, str]:
        """Return row background, foreground, tooltip, combo stylesheet."""
        if role in self._required:
            return (
                QColor(P.SUCCESS + "33"),
                QColor(P.SUCCESS_LIGHT),
                "این ستون به یک نقش الزامی نگاشت شده است.",
                self._combo_style(P.SUCCESS, P.SUCCESS_LIGHT),
            )

        if role != Role.NONE:
            return (
                QColor(P.INFO + "22"),
                QColor(P.TEXT_PRIMARY),
                "این ستون به یک نقش اختیاری/غیرالزامی نگاشت شده است.",
                self._combo_style(P.INFO, P.TEXT_PRIMARY),
            )

        if missing_required:
            missing_names = "، ".join(
                r.value for r in sorted(missing_required, key=lambda x: x.value)
            )
            return (
                QColor(P.BG_SECONDARY),
                QColor(P.TEXT_MUTED),
                "این ستون نگاشت نشده است. "
                f"نقش‌های الزامی ناقص: {missing_names}",
                self._combo_style(P.WARNING, P.TEXT_MUTED),
            )

        return (
            QColor(P.BG_SECONDARY),
            QColor(P.TEXT_MUTED),
            "این ستون نگاشت نشده است، اما همه نقش‌های الزامی تکمیل شده‌اند.",
            self._combo_style(P.BORDER, P.TEXT_MUTED),
        )

    @staticmethod
    def _combo_style(border: str, color: str) -> str:
        return (
            "QComboBox{"
            f"color:{color};"
            f"background:{P.BG_INPUT};"
            f"border:1px solid {border};"
            "border-radius:5px;"
            "padding:3px 6px;"
            "}"
            "QComboBox::drop-down{"
            "border:0;"
            "width:18px;"
            "}"
        )

    @staticmethod
    def _readonly_item(text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(str(text))
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        return item
