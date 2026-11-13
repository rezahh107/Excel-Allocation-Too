"""Normal workspace mode beside the wizard."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.utils.rtl_utils import apply_rtl
from app.utils.theme import ColorPalette as P

if TYPE_CHECKING:
    from app.ui.wizard import AllocationWizard


class _MetricCard(QFrame):
    def __init__(self, title: str, value: str = "—") -> None:
        super().__init__()
        self.setObjectName("card")
        self.setMinimumHeight(86)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        self.title_lbl = QLabel(title)
        self.title_lbl.setObjectName("lbl_muted")
        self.value_lbl = QLabel(value)
        self.value_lbl.setStyleSheet(
            f"color:{P.TEXT_PRIMARY}; font-size:22px; font-weight:bold;"
        )
        lay.addWidget(self.title_lbl)
        lay.addWidget(self.value_lbl)
        lay.addStretch()

    def set_value(self, value: str) -> None:
        self.value_lbl.setText(value)

    def set_color(self, hex_color: str) -> None:
        self.value_lbl.setStyleSheet(
            f"color:{hex_color}; font-size:22px; font-weight:bold;"
        )


class NormalWorkspace(QWidget):
    requestWizardMode = Signal(int)
    requestExport = Signal()
    requestRun = Signal()

    def __init__(self, wizard: "AllocationWizard") -> None:
        super().__init__()
        apply_rtl(self)
        self.wizard_ref = wizard

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # header
        header = QHBoxLayout()
        title = QLabel("حالت عادی / Workspace")
        title.setStyleSheet(
            f"color:{P.TEXT_PRIMARY}; font-size:20px; font-weight:bold;"
        )
        subtitle = QLabel(
            "دسترسی سریع به فایل‌ها، نگاشت، تنظیمات، اجرا و خروجی"
        )
        subtitle.setObjectName("lbl_muted")
        title_box = QVBoxLayout()
        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        self.refresh_btn = QPushButton("🔄 بروزرسانی")
        self.refresh_btn.setObjectName("btn_secondary")
        self.refresh_btn.clicked.connect(self.refresh)

        self.wizard_btn = QPushButton("🧭 رفتن به ویزارد")
        self.wizard_btn.setObjectName("btn_secondary")
        self.wizard_btn.clicked.connect(
            lambda: self.requestWizardMode.emit(-1)
        )

        self.run_btn = QPushButton("▶ اجرای سریع")
        self.run_btn.setObjectName("btn_primary")
        self.run_btn.clicked.connect(self._quick_run)

        self.export_btn = QPushButton("💾 خروجی سریع")
        self.export_btn.setObjectName("btn_secondary")
        self.export_btn.clicked.connect(self._quick_export)

        header.addLayout(title_box)
        header.addStretch()
        header.addWidget(self.refresh_btn)
        header.addWidget(self.wizard_btn)
        header.addWidget(self.run_btn)
        header.addWidget(self.export_btn)
        root.addLayout(header)

        # splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter, 1)

        # nav
        self.nav = QListWidget()
        self.nav.setMaximumWidth(230)
        self.nav.setMinimumWidth(190)
        for text, idx in [
            ("📁 فایل‌ها", 0), ("🧩 نگاشت ستون‌ها", 1),
            ("⚙ تنظیمات توزیع", 2), ("👀 پیش‌نمایش", 3),
            ("▶ اجرا", 4), ("💾 خروجی", 5),
        ]:
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, idx)
            self.nav.addItem(item)
        self.nav.itemDoubleClicked.connect(self._open_nav_item)
        splitter.addWidget(self.nav)

        # center
        center = QWidget()
        center_lay = QVBoxLayout(center)
        center_lay.setContentsMargins(0, 0, 0, 0)
        center_lay.setSpacing(10)

        # row 1: main metrics
        row1 = QGridLayout()
        row1.setSpacing(10)
        self.card_students = _MetricCard("دانش‌آموزان")
        self.card_mentors = _MetricCard("پشتیبان‌ها")
        self.card_capacity = _MetricCard("ظرفیت")
        self.card_mode = _MetricCard("حالت توزیع")
        row1.addWidget(self.card_students, 0, 0)
        row1.addWidget(self.card_mentors, 0, 1)
        row1.addWidget(self.card_capacity, 0, 2)
        row1.addWidget(self.card_mode, 0, 3)
        center_lay.addLayout(row1)

        # row 2: manager fairness
        self.manager_group = QGroupBox("آمار بار مدیرها (مشتق از راهنماها)")
        mgr_grid = QGridLayout(self.manager_group)
        mgr_grid.setSpacing(8)
        self.card_mgr_min = _MetricCard("کمترین بار مدیر")
        self.card_mgr_max = _MetricCard("بیشترین بار مدیر")
        self.card_mgr_dev = _MetricCard("حداکثر انحراف")
        self.card_mgr_bal = _MetricCard("وضعیت کلی")
        mgr_grid.addWidget(self.card_mgr_min, 0, 0)
        mgr_grid.addWidget(self.card_mgr_max, 0, 1)
        mgr_grid.addWidget(self.card_mgr_dev, 0, 2)
        mgr_grid.addWidget(self.card_mgr_bal, 0, 3)
        self.manager_group.setVisible(False)
        center_lay.addWidget(self.manager_group)

        # actions
        actions_group = QGroupBox("عملیات سریع")
        actions_lay = QGridLayout(actions_group)
        btn_load = QPushButton("📁 بارگذاری فایل‌ها")
        btn_map = QPushButton("🧩 تنظیم نگاشت")
        btn_settings = QPushButton("⚙ تنظیمات انصاف")
        btn_preview = QPushButton("👀 پیش‌نمایش تخصیص")
        btn_execute = QPushButton("▶ اجرای تخصیص")
        btn_export = QPushButton("💾 خروجی گرفتن")
        for btn in (
            btn_load, btn_map, btn_settings,
            btn_preview, btn_execute, btn_export,
        ):
            btn.setObjectName("btn_secondary")
        btn_execute.setObjectName("btn_primary")
        btn_load.clicked.connect(lambda: self.requestWizardMode.emit(0))
        btn_map.clicked.connect(lambda: self.requestWizardMode.emit(1))
        btn_settings.clicked.connect(lambda: self.requestWizardMode.emit(2))
        btn_preview.clicked.connect(lambda: self.requestWizardMode.emit(3))
        btn_execute.clicked.connect(self._quick_run)
        btn_export.clicked.connect(self._quick_export)
        actions_lay.addWidget(btn_load, 0, 0)
        actions_lay.addWidget(btn_map, 0, 1)
        actions_lay.addWidget(btn_settings, 1, 0)
        actions_lay.addWidget(btn_preview, 1, 1)
        actions_lay.addWidget(btn_execute, 2, 0)
        actions_lay.addWidget(btn_export, 2, 1)
        center_lay.addWidget(actions_group)

        self.summary_box = QGroupBox("خلاصه وضعیت")
        summary_lay = QVBoxLayout(self.summary_box)
        self.summary_lbl = QLabel("")
        self.summary_lbl.setWordWrap(True)
        self.summary_lbl.setObjectName("lbl_muted")
        summary_lay.addWidget(self.summary_lbl)
        center_lay.addWidget(self.summary_box)
        center_lay.addStretch()
        splitter.addWidget(center)

        # inspector
        inspector = QWidget()
        inspector.setMaximumWidth(330)
        inspector.setMinimumWidth(260)
        insp_lay = QVBoxLayout(inspector)
        insp_lay.setContentsMargins(0, 0, 0, 0)
        insp_lay.setSpacing(10)

        status_group = QGroupBox("Inspector")
        status_lay = QVBoxLayout(status_group)
        self.file_status = QLabel("")
        self.mapping_status = QLabel("")
        self.result_status = QLabel("")
        self.manager_status = QLabel("")
        for lbl in (
            self.file_status, self.mapping_status,
            self.result_status, self.manager_status,
        ):
            lbl.setWordWrap(True)
            lbl.setObjectName("lbl_muted")
            status_lay.addWidget(lbl)
        insp_lay.addWidget(status_group)

        hints_group = QGroupBox("راهنما")
        hints_lay = QVBoxLayout(hints_group)
        hints = QLabel(
            "برای ویرایش جزئی هر بخش، روی آیتم مربوطه دوبار کلیک "
            "کنید تا همان مرحله در ویزارد باز شود.\n\n"
            "سهم مدیر از مجموع تخصیص‌های راهنماهایش به‌دست می‌آید؛\n"
            "برابری باید میان تمام راهنماها سنجیده شود."
        )
        hints.setWordWrap(True)
        hints.setObjectName("lbl_muted")
        hints_lay.addWidget(hints)
        insp_lay.addWidget(hints_group)
        insp_lay.addStretch()
        splitter.addWidget(inspector)
        splitter.setSizes([210, 680, 300])

        self._timer = QTimer(self)
        self._timer.setInterval(1500)
        self._timer.timeout.connect(self.refresh)
        self._timer.start()
        self.refresh()

    def _open_nav_item(self, item: QListWidgetItem) -> None:
        page_index = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(page_index, int):
            if page_index == 5 and not self.wizard_ref.state.export_eligible():
                QMessageBox.warning(
                    self, "خروجی تأیید نشده",
                    "ابتدا پیش‌نمایش و تأیید معتبر را تکمیل کنید.",
                )
                self.requestWizardMode.emit(
                    3 if self.wizard_ref.state.result is not None else 0
                )
                return
            self.requestWizardMode.emit(page_index)

    def _quick_run(self) -> None:
        state = self.wizard_ref.state
        if not state.book1_rows or not state.book2_rows:
            QMessageBox.warning(
                self, "فایل‌ها ناقص است",
                "ابتدا هر دو فایل Book1 و Book2 را بارگذاری کنید.",
            )
            self.requestWizardMode.emit(0)
            return
        if getattr(state, "map_errors", None):
            QMessageBox.warning(
                self, "نگاشت ناقص است",
                "ابتدا خطاهای نگاشت ستون‌ها را برطرف کنید.",
            )
            self.requestWizardMode.emit(1)
            return
        self.requestWizardMode.emit(4)

    def _quick_export(self) -> None:
        if not self.wizard_ref.state.export_eligible():
            QMessageBox.warning(
                self, "خروجی تأیید نشده",
                "ابتدا پیش‌نمایش و تأیید معتبر را تکمیل کنید.",
            )
            self.requestWizardMode.emit(
                3 if self.wizard_ref.state.result is not None else 0
            )
            return
        self.requestExport.emit()

    def refresh(self) -> None:
        state = self.wizard_ref.state
        self.export_btn.setEnabled(state.export_eligible())
        students_count = len(state.book2_rows) if state.book2_rows else 0
        mentors_count = len(state.book1_rows) if state.book1_rows else 0

        self.card_students.set_value(
            str(students_count) if students_count else "—"
        )
        self.card_mentors.set_value(
            str(mentors_count) if mentors_count else "—"
        )
        self.card_capacity.set_value(
            str(state.result.capacity)
            if state.result is not None else "—"
        )
        self.card_mode.set_value(state.fairness.value)

        # manager fairness cards
        if state.result is not None:
            from app.services.simulation_service import manager_report
            mgr = manager_report(state.result)
            if mgr["managers"]:
                self.manager_group.setVisible(True)
                self.card_mgr_min.set_value(str(mgr["min_load"]))
                self.card_mgr_max.set_value(str(mgr["max_load"]))
                self.card_mgr_dev.set_value(str(mgr["max_deviation"]))
                self.card_mgr_bal.set_value("سهم مستقل ندارد")
                self.card_mgr_bal.set_color(P.TEXT_MUTED)

                self.manager_status.setText(
                    "📊 مدیرها\n"
                    + "\n".join(
                        f"{m}: {mgr['loads'].get(m, 0)} "
                        f"(هدف: {mgr['targets'].get(m, 0):.1f})"
                        f" [{mgr['deviations'].get(m, 0):+.1f}]"
                        for m in mgr["managers"]
                    )
                )
            else:
                self.manager_group.setVisible(False)
                self.manager_status.setText(
                    "📊 مدیرها\nاطلاعات مدیر در داده‌ها یافت نشد."
                )
        else:
            self.manager_group.setVisible(False)
            self.manager_status.setText(
                "📊 مدیرها\n⏳ هنوز تخصیص اجرا نشده"
            )

        book1_ok = bool(state.book1_rows)
        book2_ok = bool(state.book2_rows)
        self.file_status.setText(
            "📁 فایل‌ها\n"
            f"Book1: {'✅ بارگذاری شده' if book1_ok else '❌ بارگذاری نشده'}\n"
            f"Book2: {'✅ بارگذاری شده' if book2_ok else '❌ بارگذاری نشده'}"
        )

        errors = getattr(state, "map_errors", [])
        if errors:
            self.mapping_status.setText(
                "🧩 نگاشت\n❌ دارای خطا:\n"
                + "\n".join(f"• {e}" for e in errors[:5])
            )
        elif state.map1 or state.map2:
            self.mapping_status.setText("🧩 نگاشت\n✅ آماده")
        else:
            self.mapping_status.setText("🧩 نگاشت\n⏳ هنوز تنظیم نشده")

        if state.result is not None:
            loads = state.result.load_per_mentor()
            min_l = min(loads.values()) if loads else 0
            max_l = max(loads.values()) if loads else 0
            self.result_status.setText(
                "📊 نتیجه\n✅ تخصیص موجود\n"
                f"ظرفیت: {state.result.capacity}\n"
                f"بار پشتیبان: {min_l}–{max_l}\n"
                f"تخصیص جدید: {state.result.num_new}\n"
                f"تثبیت‌نشده: {state.result.num_non_stabilized}\n"
                f"جابه‌جا شده: {state.result.num_moved}"
            )
        else:
            self.result_status.setText(
                "📊 نتیجه\n⏳ هنوز اجرا نشده"
            )

        self.summary_lbl.setText(
            f"دانش‌آموزان: {students_count or '—'}\n"
            f"پشتیبان‌ها: {mentors_count or '—'}\n"
            f"حالت توزیع: {state.fairness.value}\n"
            f"وضعیت فایل‌ها: "
            f"{'کامل' if book1_ok and book2_ok else 'ناقص'}\n"
            f"وضعیت خروجی: "
            f"{'آماده' if state.export_eligible() else 'نیازمند تأیید'}"
        )
