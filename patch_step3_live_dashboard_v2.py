"""Patch: Step3 Live Preview Dashboard v2 (fixes from review).

Fixes:
    - Proper FairnessMode enum comparison (no more string compare)
    - Debounce for capacity_spin.valueChanged
    - Proper logging in _refresh_dashboard
    - Implementation of sync_from_state() for wizard compatibility
    - Rebalance section now correctly activates on MANAGER_BALANCED
    - More informative rebalance display (even before backend exposes move count)

Run:
    python patch_step3_live_dashboard_v2.py
    python tools/smoke_check.py
    python -m app.main
"""
from __future__ import annotations

import py_compile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
STEP3 = ROOT / "app" / "ui" / "pages" / "step3_settings.py"
DASHBOARD = ROOT / "app" / "ui" / "widgets" / "mini_dashboard.py"


STEP3_PATCH = '''"""Step 3 — distribution settings."""
from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWizardPage,
)

from app.core.models import FairnessMode, WizardState
from app.utils.logger import get_logger
from app.utils.rtl_utils import apply_rtl
from app.utils.theme import ColorPalette as P
from app.ui.widgets.mini_dashboard import MiniDashboard
from app.services.domain_service import build_domain
from app.services.simulation_service import simulate

log = get_logger("step3_settings")


_FAIRNESS_DESCRIPTIONS: dict[FairnessMode, str] = {
    FairnessMode.ORIGINAL: (
        "هر دانش‌آموز تا حد امکان پیش پشتیبان اولیه‌اش می‌ماند. "
        "عدالت بین پشتیبان‌ها تضمین نمی‌شود."
    ),
    FairnessMode.ROUND_ROBIN: (
        "دانش‌آموزان به‌صورت نوبتی به پشتیبان‌ها اختصاص می‌یابند. "
        "توزیع کلی نسبتاً عادلانه است."
    ),
    FairnessMode.MENTOR_BALANCED: (
        "بار کاری پشتیبان‌ها تا حد ممکن مساوی می‌شود. "
        "بهترین انتخاب برای عدالت بین پشتیبان‌ها."
    ),
    FairnessMode.MANAGER_BALANCED: (
        "ابتدا بار کاری مدیرها به‌صورت متناسب با تعداد پشتیبان‌ها "
        "توزیع می‌شود، سپس داخل هر مدیر بین پشتیبان‌ها عادلانه "
        "تقسیم می‌شود. ✅ پیشنهاد برای عدالت در کل سازمان."
    ),
}


class Step3Settings(QWizardPage):
    """Step 3: allocation settings with live preview."""

    def __init__(self, state: WizardState) -> None:
        super().__init__()
        apply_rtl(self)

        self.state = state
        self.setTitle("مرحله ۳: تنظیمات توزیع")
        self.setSubTitle(
            "حالت توزیع، ظرفیت و تنظیمات اضافی را انتخاب کنید."
        )

        lay = QVBoxLayout(self)

        # ── fairness ─────────────────────────────────────────────
        fair_group = QGroupBox("حالت توزیع عادلانه")
        fair_lay = QVBoxLayout(fair_group)

        self.fairness_combo = QComboBox()
        for mode in FairnessMode:
            self.fairness_combo.addItem(mode.value, mode)

        idx = self.fairness_combo.findData(self.state.fairness)
        if idx >= 0:
            self.fairness_combo.setCurrentIndex(idx)

        self.fairness_desc = QLabel("")
        self.fairness_desc.setObjectName("lbl_muted")
        self.fairness_desc.setWordWrap(True)
        self.fairness_desc.setMinimumHeight(60)

        self.fairness_combo.currentIndexChanged.connect(
            self._update_fairness_desc
        )
        self._update_fairness_desc()

        fair_lay.addWidget(self.fairness_combo)
        fair_lay.addWidget(self.fairness_desc)
        lay.addWidget(fair_group)

        # ── capacity ──────────────────────────────────────────────
        cap_group = QGroupBox("ظرفیت")
        cap_form = QFormLayout(cap_group)

        self.auto_capacity = QCheckBox("محاسبه خودکار ظرفیت")
        self.auto_capacity.setChecked(state.capacity_override is None)
        self.auto_capacity.toggled.connect(self._toggle_capacity)

        self.capacity_spin = QSpinBox()
        self.capacity_spin.setRange(1, 9999)
        self.capacity_spin.setValue(state.capacity_override or 5)
        self.capacity_spin.setEnabled(state.capacity_override is not None)

        cap_form.addRow(self.auto_capacity)
        cap_form.addRow("ظرفیت دستی:", self.capacity_spin)
        lay.addWidget(cap_group)

        # ── stabilisation ─────────────────────────────────────────
        stab_group = QGroupBox("تثبیت دانش‌آموزان")
        stab_lay = QVBoxLayout(stab_group)

        self.stabilize_chk = QCheckBox(
            "دانش‌آموزانی که پشتیبان اولیه دارند تثبیت شوند"
        )
        self.stabilize_chk.setChecked(state.stabilize_initial)
        stab_lay.addWidget(self.stabilize_chk)

        stab_info = QLabel(
            "دانش‌آموزان تثبیت‌شده هرگز جابه‌جا نمی‌شوند، "
            "حتی در مرحله Drag and Drop."
        )
        stab_info.setObjectName("lbl_muted")
        stab_info.setWordWrap(True)
        stab_lay.addWidget(stab_info)
        lay.addWidget(stab_group)

        # ── live dashboard ───────────────────────────
        self.dashboard = MiniDashboard()
        lay.addWidget(self.dashboard)

        # Debounced live connections
        self.fairness_combo.currentIndexChanged.connect(self._refresh_dashboard)
        self.auto_capacity.toggled.connect(self._refresh_dashboard)
        self.stabilize_chk.toggled.connect(self._refresh_dashboard)

        # Debounce for spinbox (prevents multiple simulates on typing)
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(300)
        self._debounce_timer.timeout.connect(self._refresh_dashboard)
        self.capacity_spin.valueChanged.connect(self._debounce_timer.start)

        lay.addStretch()

    def sync_from_state(self) -> None:
        """Sync widgets from wizard state (used by project load)."""
        idx = self.fairness_combo.findData(self.state.fairness)
        if idx >= 0:
            self.fairness_combo.setCurrentIndex(idx)

        is_auto = self.state.capacity_override is None
        self.auto_capacity.setChecked(is_auto)
        self.capacity_spin.setEnabled(not is_auto)

        if self.state.capacity_override is not None:
            self.capacity_spin.setValue(self.state.capacity_override)

        self.stabilize_chk.setChecked(self.state.stabilize_initial)
        self._refresh_dashboard()

    def _update_fairness_desc(self) -> None:
        mode: FairnessMode = self.fairness_combo.currentData()
        desc = _FAIRNESS_DESCRIPTIONS.get(mode, "")
        self.fairness_desc.setText(desc)
        if mode == FairnessMode.MANAGER_BALANCED:
            self.fairness_desc.setStyleSheet(
                f"color:{P.SUCCESS_LIGHT}; font-style:italic;"
            )
        else:
            self.fairness_desc.setStyleSheet(f"color:{P.TEXT_MUTED};")

    def initializePage(self) -> None:  # noqa: N802
        self._refresh_dashboard()

    def _refresh_dashboard(self) -> None:
        """Refresh live dashboard. Logs errors instead of silent fail."""
        try:
            fairness = self.fairness_combo.currentData()
            capacity = (
                None
                if self.auto_capacity.isChecked()
                else self.capacity_spin.value()
            )
            stabilize = self.stabilize_chk.isChecked()

            students, mentors = build_domain(self.state)
            result = simulate(
                students,
                mentors,
                fairness,
                capacity=capacity,
                stabilize_initial=stabilize,
            )

            self.dashboard.update_from(
                students, mentors, result, fairness_mode=fairness
            )
        except Exception as exc:
            log.warning("Step3 dashboard refresh failed: %s", exc)
            if hasattr(self, "dashboard"):
                self.dashboard.show_placeholder()

    def _toggle_capacity(self, auto: bool) -> None:
        self.capacity_spin.setEnabled(not auto)

    def validatePage(self) -> bool:  # noqa: N802
        self.state.fairness = self.fairness_combo.currentData()
        self.state.capacity_override = (
            None
            if self.auto_capacity.isChecked()
            else self.capacity_spin.value()
        )
        self.state.stabilize_initial = self.stabilize_chk.isChecked()
        return True

    def isComplete(self) -> bool:  # noqa: N802
        return True
'''

DASHBOARD_PATCH = '''"""MiniDashboard — live read-only allocation stats widget for Step 3.

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
        if mgr.get("managers"):
            max_dev = self._as_float(mgr.get("max_deviation", 0.0))
            if max_dev > 1.0:
                warnings.append(
                    f"توزیع بین مدیرها از هدف فاصله دارد (حداکثر انحراف: {self._fmt_float(max_dev)})."
                )
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

        self.card_manager_b.set_value(f"±{self._fmt_float(max_dev)}", hint, color)

        loads = mgr.get("loads") or {}
        targets = mgr.get("targets") or {}
        deviations = mgr.get("deviations") or {}

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
                f"{name}: {load_val}/{self._fmt_float(target_val)} ({self._fmt_signed_float(dev_val)})"
            )

        if len(parts) > 1:
            self._manager_detail.setText("  |  ".join(parts))
            self._manager_detail.show()
        else:
            self._manager_detail.hide()

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
'''

def main() -> None:
    for path, new_code in [(STEP3, STEP3_PATCH), (DASHBOARD, DASHBOARD_PATCH)]:
        if not path.exists():
            print(f"⚠ فایل پیدا نشد: {path}")
            continue

        backup = path.with_suffix(path.suffix + ".bak_step3_dashboard_v2")
        if not backup.exists():
            backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"✓ backup: {backup.name}")

        path.write_text(new_code, encoding="utf-8")
        py_compile.compile(str(path), doraise=True)
        print(f"✓ {path.name} به‌روزرسانی شد (v2)")

    print("\n✅ پچ Step3 Live Preview Dashboard v2 اعمال شد.")
    print("Run:")
    print("    python tools\\smoke_check.py")
    print("    python -m app.main")


if __name__ == "__main__":
    main()