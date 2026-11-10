"""MiniDashboard — live read-only allocation stats widget for Step 3.

v2: Proper enum handling for rebalance section + improved display.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QLabel,
    QVBoxLayout,
)

from app.core.models import FairnessMode
from app.utils.logger import get_logger
from app.utils.theme import ColorPalette as P

log = get_logger("mini_dashboard")


class _StatCard(QFrame):
    """Single compact stat card."""

    def __init__(self, title: str) -> None:
        super().__init__()
        self.setObjectName("statCard")
        self._apply_base_style()

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(2)

        self._title = QLabel(title)
        self._title.setAlignment(Qt.AlignCenter)
        self._title.setStyleSheet(
            f"color:{P.TEXT_MUTED};font-size:11px;font-weight:500;"
        )

        self._value = QLabel("—")
        self._value.setAlignment(Qt.AlignCenter)
        self._value.setStyleSheet(
            f"color:{P.TEXT_PRIMARY};font-size:22px;font-weight:bold;"
        )

        self._hint = QLabel("")
        self._hint.setAlignment(Qt.AlignCenter)
        self._hint.setStyleSheet(
            f"color:{P.TEXT_SECONDARY};font-size:10px;"
        )
        self._hint.setWordWrap(True)

        lay.addWidget(self._title)
        lay.addWidget(self._value)
        lay.addWidget(self._hint)

    def _apply_base_style(self) -> None:
        self.setStyleSheet(
            "QFrame#statCard{"
            f"background:{P.BG_SURFACE};"
            f"border:1px solid {P.BORDER};"
            "border-radius:8px;"
            "}"
        )

    def set_value(
        self,
        value: str,
        hint: str = "",
        color: str | None = None,
    ) -> None:
        self._value.setText(value)
        self._hint.setText(hint)
        self._value.setStyleSheet(
            f"color:{color or P.TEXT_PRIMARY};"
            "font-size:22px;font-weight:bold;"
        )


class MiniDashboard(QGroupBox):
    """Live read-only dashboard with correct Rebalance support."""

    def __init__(self) -> None:
        super().__init__("📊 پیش‌نمایش زنده توزیع")
        self.setLayoutDirection(Qt.RightToLeft)
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(8)

        grid = QGridLayout()
        grid.setSpacing(8)

        self.card_students = _StatCard("دانش‌آموز")
        self.card_mentors = _StatCard("پشتیبان")
        self.card_capacity = _StatCard("ظرفیت")
        self.card_mentor_b = _StatCard("توازن پشتیبان")
        self.card_manager_b = _StatCard("بار مدیرها")

        cards = [
            self.card_students,
            self.card_mentors,
            self.card_capacity,
            self.card_mentor_b,
            self.card_manager_b,
        ]
        for col, card in enumerate(cards):
            grid.addWidget(card, 0, col)

        outer.addLayout(grid)

        # Rebalance impact (fixed in v2)
        self._rebalance_box = QLabel("")
        self._rebalance_box.setWordWrap(True)
        self._rebalance_box.setAlignment(Qt.AlignCenter)
        self._rebalance_box.setStyleSheet(
            f"color:{P.SUCCESS_LIGHT};"
            "font-size:11px;"
            f"background:{P.BG_SURFACE};"
            f"border:1px solid {P.SUCCESS_LIGHT};"
            "border-radius:4px;"
            "padding:5px 8px;"
        )
        self._rebalance_box.hide()
        outer.addWidget(self._rebalance_box)

        self._manager_detail = QLabel("")
        self._manager_detail.setWordWrap(True)
        self._manager_detail.setAlignment(Qt.AlignCenter)
        self._manager_detail.setStyleSheet(
            f"color:{P.TEXT_SECONDARY};"
            "font-size:11px;"
            f"background:{P.BG_SURFACE};"
            f"border:1px solid {P.BORDER};"
            "border-radius:4px;"
            "padding:6px 8px;"
        )
        self._manager_detail.hide()
        outer.addWidget(self._manager_detail)

        self._warn = QLabel("")
        self._warn.setWordWrap(True)
        self._warn.setAlignment(Qt.AlignCenter)
        self._warn.setStyleSheet(
            f"color:{P.ERROR};"
            "font-size:11px;"
            "font-weight:bold;"
            f"background:{P.BG_SURFACE};"
            f"border:1px solid {P.ERROR};"
            "border-radius:4px;"
            "padding:4px 8px;"
        )
        self._warn.hide()
        outer.addWidget(self._warn)

    # ── Public API ────────────────────────────────────────────────
    def show_placeholder(self) -> None:
        for card in (
            self.card_students,
            self.card_mentors,
            self.card_capacity,
            self.card_mentor_b,
            self.card_manager_b,
        ):
            card.set_value("—")

        self._rebalance_box.setText("")
        self._rebalance_box.hide()
        self._manager_detail.setText("")
        self._manager_detail.hide()
        self._warn.setText("")
        self._warn.hide()

    def update_from(
        self, students, mentors, result, fairness_mode=None
    ) -> None:
        try:
            self._update_impl(students, mentors, result, fairness_mode)
        except Exception as exc:
            log.warning("MiniDashboard update failed: %s", exc)
            self.show_placeholder()

    def _update_impl(self, students, mentors, result, fairness_mode) -> None:
        n_students = len(students) if students else 0
        n_mentors = len(mentors) if mentors else 0

        self.card_students.set_value(str(n_students))
        self.card_mentors.set_value(str(n_mentors))

        if result is None or n_mentors == 0:
            for card in (self.card_capacity, self.card_mentor_b, self.card_manager_b):
                card.set_value("—")
            self._rebalance_box.hide()
            self._manager_detail.hide()
            self._warn.hide()
            return

        cap = getattr(result, "capacity", 0) or 0
        self.card_capacity.set_value(str(cap), "بیشینه هر پشتیبان")

        loads_map = (
            result.load_per_mentor()
            if callable(getattr(result, "load_per_mentor", None))
            else {}
        )
        loads = list(loads_map.values()) if loads_map else []

        mentor_spread = 0
        if loads:
            mx, mn = max(loads), min(loads)
            mentor_spread = mx - mn
            color = self._spread_color(mentor_spread, low=1, mid=3)
            self.card_mentor_b.set_value(
                f"±{mentor_spread}", f"{mn} … {mx} نفر", color
            )
        else:
            self.card_mentor_b.set_value("—", "")

        # Rebalance section - fixed enum comparison
        self._update_rebalance_section(result, fairness_mode)

        mgr = self._safe_manager_report(result)
        self._apply_manager_diagnostics(mgr)

        # Warnings
        warnings: list[str] = []
        if mentor_spread > 3:
            warnings.append(f"اختلاف بار پشتیبان‌ها زیاد است (±{mentor_spread}).")
        if loads and cap and max(loads) > cap:
            warnings.append("⚠ برخی پشتیبان‌ها از ظرفیت عبور کرده‌اند.")

        if warnings:
            self._warn.setText("  |  ".join(warnings))
            self._warn.show()
        else:
            self._warn.hide()

    def _update_rebalance_section(self, result, fairness_mode) -> None:
        """Show rebalance info only for MANAGER_BALANCED (fixed in v2)."""
        if fairness_mode != FairnessMode.MANAGER_BALANCED:
            self._rebalance_box.hide()
            return

        rebalance_moves = 0
        try:
            if hasattr(result, "rebalance_moves"):
                rebalance_moves = int(getattr(result, "rebalance_moves", 0))
            elif hasattr(result, "metadata") and isinstance(result.metadata, dict):
                rebalance_moves = int(result.metadata.get("rebalance_moves", 0))
        except Exception:
            pass

        if rebalance_moves > 0:
            text = f"🔄 Rebalance Pass فعال — {rebalance_moves} شیفت برای تعادل مدیرها"
        else:
            # Show that rebalance is active even if exact count not yet exposed by simulation
            text = "🔄 Rebalance Pass فعال (توزیع بین مدیرها بهینه‌سازی می‌شود)"

        self._rebalance_box.setText(text)
        self._rebalance_box.show()

    def _apply_manager_diagnostics(self, mgr: dict) -> None:
        """Manager totals are descriptive; fairness is only per mentor."""
        managers = mgr.get("managers") or []
        if not isinstance(managers, list) or not managers:
            self.card_manager_b.set_value("—", "نامشخص")
            self._manager_detail.hide()
            return

        min_load = self._as_int(mgr.get("min_load", 0))
        max_load = self._as_int(mgr.get("max_load", 0))
        self.card_manager_b.set_value(
            f"{min_load} … {max_load}", "تعداد مشتق از راهنماها"
        )
        loads = mgr.get("loads") or {}
        leaders = sorted(managers, key=lambda name: loads.get(name, 0), reverse=True)[:3]
        parts = ["مدیرها سهم مستقل ندارند"] + [
            f"{name}: {self._as_int(loads.get(name, 0))} نفر"
            for name in leaders
        ]
        self._manager_detail.setText("  |  ".join(parts))
        self._manager_detail.show()

    def _safe_manager_report(self, result) -> dict:
        try:
            from app.services.simulation_service import manager_report
            data = manager_report(result)
            return data if isinstance(data, dict) else {}
        except Exception as exc:
            log.debug("manager_report unavailable: %s", exc)
            return {}

    # ── Helpers ───────────────────────────────────────────────────
    @staticmethod
    def _spread_color(spread: int, low: int, mid: int) -> str:
        if spread <= low:
            return P.SUCCESS_LIGHT
        if spread <= mid:
            return P.WARNING
        return P.ERROR

    @staticmethod
    def _manager_color(max_dev: float) -> str:
        if max_dev <= 1.0:
            return P.SUCCESS_LIGHT
        if max_dev <= 3.0:
            return P.WARNING
        return P.ERROR

    @staticmethod
    def _as_float(value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _as_int(value) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _fmt_float(value: float) -> str:
        return f"{value:.1f}"

    @staticmethod
    def _fmt_signed_float(value: float) -> str:
        return f"{value:+.1f}"
