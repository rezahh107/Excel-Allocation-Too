"""Step 3 — distribution settings."""
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
