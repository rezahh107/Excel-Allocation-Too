"""MiniDashboard — live read-only allocation stats widget for Step 3.

Colour names are aligned with the project's ColorPalette:
    BG_SURFACE / BORDER / TEXT_PRIMARY / TEXT_MUTED
    SUCCESS_LIGHT / WARNING / ERROR / TEXT_SECONDARY

Public API:
    dashboard.show_placeholder()                     -> reset all cards to —
    dashboard.update_from(students, mentors, result) -> refresh everything
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

from app.utils.logger import get_logger
from app.utils.theme import ColorPalette as P

log = get_logger("mini_dashboard")


class _StatCard(QFrame):
    """Single compact stat card: icon-title on top, big value, small hint."""

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
    """Live read-only dashboard wired into Step 3.

    Safe to call with None/empty data — shows placeholder dashes.
    Exceptions are logged and suppressed so the wizard is never broken.
    """

    def __init__(self) -> None:
        super().__init__("📊 پیش‌نمایش زنده توزیع")
        self.setLayoutDirection(Qt.RightToLeft)
        self._build_ui()

    # ── UI construction ───────────────────────────────────────────
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
        self.card_manager_b = _StatCard("توازن مدیر")

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
        """Reset all cards to — (used before any data is loaded)."""
        for card in (
            self.card_students,
            self.card_mentors,
            self.card_capacity,
            self.card_mentor_b,
            self.card_manager_b,
        ):
            card.set_value("—")

        self._manager_detail.setText("")
        self._manager_detail.hide()

        self._warn.setText("")
        self._warn.hide()

    def update_from(self, students, mentors, result) -> None:
        """Refresh dashboard. Fully defensive — never raises."""
        try:
            self._update_impl(students, mentors, result)
        except Exception as exc:
            log.warning("MiniDashboard update failed: %s", exc)
            self.show_placeholder()

    # ── Implementation ────────────────────────────────────────────
    def _update_impl(self, students, mentors, result) -> None:
        n_students = len(students) if students else 0
        n_mentors = len(mentors) if mentors else 0

        self.card_students.set_value(str(n_students))
        self.card_mentors.set_value(str(n_mentors))

        if result is None or n_mentors == 0:
            for card in (
                self.card_capacity,
                self.card_mentor_b,
                self.card_manager_b,
            ):
                card.set_value("—")
            self._manager_detail.setText("")
            self._manager_detail.hide()
            self._warn.setText("")
            self._warn.hide()
            return

        cap = getattr(result, "capacity", 0) or 0
        self.card_capacity.set_value(str(cap), "بیشینه هر پشتیبان")

        loads_map: dict = (
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
                f"±{mentor_spread}",
                f"{mn} … {mx} نفر",
                color,
            )
        else:
            self.card_mentor_b.set_value("—", "")

        mgr = self._safe_manager_report(result)
        self._apply_manager_diagnostics(mgr)

        warnings: list[str] = []
        if mentor_spread > 3:
            warnings.append(
                f"اختلاف بار پشتیبان‌ها زیاد است (±{mentor_spread})."
            )

        if mgr.get("managers"):
            max_dev = self._as_float(mgr.get("max_deviation", 0.0))
            if max_dev > 1.0:
                warnings.append(
                    "توزیع بین مدیرها از هدف فاصله دارد "
                    f"(حداکثر انحراف: {self._fmt_float(max_dev)})."
                )

        if loads and cap and max(loads) > cap:
            warnings.append("⚠ برخی پشتیبان‌ها از ظرفیت عبور کرده‌اند.")

        if warnings:
            self._warn.setText("  |  ".join(warnings))
            self._warn.show()
        else:
            self._warn.setText("")
            self._warn.hide()

    def _apply_manager_diagnostics(self, mgr: dict) -> None:
        managers = mgr.get("managers") or []
        if not isinstance(managers, list) or not managers:
            self.card_manager_b.set_value("—", "نامشخص")
            self._manager_detail.setText("")
            self._manager_detail.hide()
            return

        max_dev = self._as_float(mgr.get("max_deviation", 0.0))
        balanced = bool(mgr.get("is_balanced", False))
        color = self._manager_color(max_dev)

        min_load = self._as_int(mgr.get("min_load", 0))
        max_load = self._as_int(mgr.get("max_load", 0))
        hint = f"{min_load} … {max_load} نفر"

        self.card_manager_b.set_value(
            f"±{self._fmt_float(max_dev)}",
            hint,
            color,
        )

        loads = mgr.get("loads") if isinstance(mgr.get("loads"), dict) else {}
        targets = (
            mgr.get("targets")
            if isinstance(mgr.get("targets"), dict)
            else {}
        )
        deviations = (
            mgr.get("deviations")
            if isinstance(mgr.get("deviations"), dict)
            else {}
        )

        ranked = sorted(
            [name for name in managers if isinstance(name, str)],
            key=lambda name: abs(self._as_float(deviations.get(name, 0.0))),
            reverse=True,
        )

        top = ranked[:3]
        status = "متعادل" if balanced else "نیازمند تنظیم"

        parts = [f"وضعیت مدیرها: {status}"]
        for name in top:
            load_val = self._as_int(loads.get(name, 0))
            target_val = self._as_float(targets.get(name, 0.0))
            dev_val = self._as_float(deviations.get(name, 0.0))
            parts.append(
                f"{name}: "
                f"{load_val}/{self._fmt_float(target_val)} "
                f"({self._fmt_signed_float(dev_val)})"
            )

        if len(parts) > 1:
            self._manager_detail.setText("  |  ".join(parts))
            self._manager_detail.show()
        else:
            self._manager_detail.setText("")
            self._manager_detail.hide()

    def _safe_manager_report(self, result) -> dict:
        """Lazy-import and safely call manager_report()."""
        try:
            from app.services.simulation_service import manager_report
        except Exception as exc:
            log.debug("manager_report import unavailable: %s", exc)
            return {}

        try:
            data = manager_report(result)
        except Exception as exc:
            log.warning("manager_report failed: %s", exc)
            return {}

        return data if isinstance(data, dict) else {}

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
