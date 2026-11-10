"""Application main window with Wizard and Normal modes.

This shell hosts:
    - Existing AllocationWizard
    - NormalWorkspace dashboard

It keeps the original wizard intact while adding a professional application
frame around it.
"""
from __future__ import annotations

from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QToolBar,
    QWidget,
)

from app.ui.normal_workspace import NormalWorkspace
from app.ui.wizard import AllocationWizard
from app.utils.rtl_utils import apply_rtl
from app.utils.theme import ColorPalette as P


_ORG = "ClaudeOpus"
_APP = "ExcelAllocationTool"


class MainWindow(QMainWindow):
    """Main app shell that hosts Wizard and Normal workspace modes."""

    MODE_WIZARD = 0
    MODE_NORMAL = 1

    def __init__(self) -> None:
        super().__init__()
        apply_rtl(self)

        self.settings = QSettings(_ORG, _APP)

        self.setWindowTitle("سامانه تخصیص پشتیبان · Workspace")
        self.resize(1180, 820)

        # Existing wizard is preserved as-is.
        self.wizard = AllocationWizard()

        # Normal mode reuses wizard state.
        self.normal_workspace = NormalWorkspace(self.wizard)
        self.normal_workspace.requestWizardMode.connect(self._open_wizard_page)
        self.normal_workspace.requestExport.connect(self._export_from_normal)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.wizard)
        self.stack.addWidget(self.normal_workspace)
        self.setCentralWidget(self.stack)

        self._build_toolbar()
        self._build_status_bar()
        self._setup_shortcuts()
        self._restore_window_settings()

        self.stack.currentChanged.connect(self._on_mode_changed)

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(1500)
        self._refresh_timer.timeout.connect(self.refresh_shell_status)
        self._refresh_timer.start()

        self.refresh_shell_status()

    # ── UI shell ────────────────────────────────────────────────
    def _build_toolbar(self) -> None:
        """Create top toolbar with mode switch and quick actions."""
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setAllowedAreas(Qt.ToolBarArea.TopToolBarArea)
        toolbar.setStyleSheet(
            f"QToolBar{{background:{P.BG_SURFACE};"
            f"border-bottom:1px solid {P.BORDER}; spacing:8px;}}"
            f"QLabel{{color:{P.TEXT_MUTED}; padding:0 6px;}}"
        )
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

        title = QLabel("حالت کاری:")
        toolbar.addWidget(title)

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("حالت ویزارد", self.MODE_WIZARD)
        self.mode_combo.addItem("حالت عادی / Workspace", self.MODE_NORMAL)
        self.mode_combo.currentIndexChanged.connect(self._switch_mode_from_combo)
        toolbar.addWidget(self.mode_combo)

        spacer = QWidget()
        spacer.setMinimumWidth(20)
        toolbar.addWidget(spacer)

        self.btn_files = QPushButton("📁 فایل‌ها")
        self.btn_mapping = QPushButton("🧩 نگاشت")
        self.btn_settings = QPushButton("⚙ تنظیمات")
        self.btn_preview = QPushButton("👀 پیش‌نمایش")
        self.btn_run = QPushButton("▶ اجرا")
        self.btn_export = QPushButton("💾 خروجی")

        for btn in (
            self.btn_files,
            self.btn_mapping,
            self.btn_settings,
            self.btn_preview,
            self.btn_export,
        ):
            btn.setObjectName("btn_secondary")
            toolbar.addWidget(btn)

        self.btn_run.setObjectName("btn_primary")
        toolbar.addWidget(self.btn_run)

        self.btn_files.clicked.connect(lambda: self._open_wizard_page(0))
        self.btn_mapping.clicked.connect(lambda: self._open_wizard_page(1))
        self.btn_settings.clicked.connect(lambda: self._open_wizard_page(2))
        self.btn_preview.clicked.connect(lambda: self._open_wizard_page(3))
        self.btn_run.clicked.connect(self._run_from_toolbar)
        self.btn_export.clicked.connect(self._export_from_normal)

    def _build_status_bar(self) -> None:
        """Create persistent MainWindow status bar."""
        bar = self.statusBar()
        bar.setStyleSheet(
            f"QStatusBar{{background:{P.BG_SURFACE};"
            f"color:{P.TEXT_MUTED};"
            f"border-top:1px solid {P.BORDER};}}"
            f"QLabel{{color:{P.TEXT_MUTED}; padding:0 8px;}}"
        )

        self.sb_mode = QLabel("حالت: —")
        self.sb_files = QLabel("فایل‌ها: —")
        self.sb_students = QLabel("دانش‌آموز: —")
        self.sb_mentors = QLabel("پشتیبان: —")
        self.sb_result = QLabel("نتیجه: —")

        for lbl in (
            self.sb_mode,
            self.sb_files,
            self.sb_students,
            self.sb_mentors,
            self.sb_result,
        ):
            bar.addPermanentWidget(lbl)

        bar.showMessage("آماده")

    def _setup_shortcuts(self) -> None:
        """Register application-level shortcuts."""
        QShortcut(QKeySequence("Ctrl+1"), self, self._switch_to_wizard)
        QShortcut(QKeySequence("Ctrl+2"), self, self._switch_to_normal)
        QShortcut(QKeySequence("Ctrl+O"), self, lambda: self._open_wizard_page(0))
        QShortcut(QKeySequence("Ctrl+S"), self, self._export_from_normal)
        QShortcut(QKeySequence("F5"), self, self._run_from_toolbar)
        QShortcut(QKeySequence("F1"), self, self._show_help)

    # ── mode switching ──────────────────────────────────────────
    def _switch_mode_from_combo(self) -> None:
        """Switch central widget based on combo selection."""
        mode = self.mode_combo.currentData()

        if mode == self.MODE_NORMAL:
            self.stack.setCurrentWidget(self.normal_workspace)
            self.normal_workspace.refresh()
            self.statusBar().showMessage("حالت عادی فعال شد", 2500)
        else:
            self.stack.setCurrentWidget(self.wizard)
            self.statusBar().showMessage("حالت ویزارد فعال شد", 2500)

        self.refresh_shell_status()

    def _switch_to_wizard(self) -> None:
        idx = self.mode_combo.findData(self.MODE_WIZARD)
        if idx >= 0:
            self.mode_combo.setCurrentIndex(idx)
        else:
            self.stack.setCurrentWidget(self.wizard)

    def _switch_to_normal(self) -> None:
        idx = self.mode_combo.findData(self.MODE_NORMAL)
        if idx >= 0:
            self.mode_combo.setCurrentIndex(idx)
        else:
            self.stack.setCurrentWidget(self.normal_workspace)

    def _on_mode_changed(self, _index: int) -> None:
        """Synchronise combo and status after stacked widget changes."""
        if self.stack.currentWidget() is self.normal_workspace:
            idx = self.mode_combo.findData(self.MODE_NORMAL)
            self.normal_workspace.refresh()
        else:
            idx = self.mode_combo.findData(self.MODE_WIZARD)

        if idx >= 0 and self.mode_combo.currentIndex() != idx:
            self.mode_combo.blockSignals(True)
            self.mode_combo.setCurrentIndex(idx)
            self.mode_combo.blockSignals(False)

        self.refresh_shell_status()

    # ── wizard navigation / commands ────────────────────────────
    def _open_wizard_page(self, page_index: int) -> None:
        """Switch to wizard mode and optionally open a specific page.

        page_index:
            -1 means switch to wizard without changing current page.
             0..5 navigates to the respective wizard page.
        """
        self.stack.setCurrentWidget(self.wizard)

        idx = self.mode_combo.findData(self.MODE_WIZARD)
        if idx >= 0 and self.mode_combo.currentIndex() != idx:
            self.mode_combo.blockSignals(True)
            self.mode_combo.setCurrentIndex(idx)
            self.mode_combo.blockSignals(False)

        if page_index >= 0:
            page_ids = self.wizard.pageIds()
            if page_index < len(page_ids):
                try:
                    self.wizard.setCurrentId(page_ids[page_index])
                except Exception as exc:  # noqa: BLE001
                    self.statusBar().showMessage(
                        f"خطا در باز کردن مرحله: {exc}",
                        4000,
                    )

        if hasattr(self.wizard, "refresh_status"):
            self.wizard.refresh_status()

        self.refresh_shell_status()

    def _run_from_toolbar(self) -> None:
        """Navigate to execution step with basic validation."""
        state = self.wizard.state

        if not state.book1_rows or not state.book2_rows:
            QMessageBox.warning(
                self,
                "فایل‌ها ناقص است",
                "ابتدا هر دو فایل Book1 و Book2 را بارگذاری کنید.",
            )
            self._open_wizard_page(0)
            return

        map_errors = getattr(state, "map_errors", [])
        if map_errors:
            QMessageBox.warning(
                self,
                "نگاشت ناقص است",
                "ابتدا خطاهای نگاشت ستون‌ها را برطرف کنید.",
            )
            self._open_wizard_page(1)
            return

        self._open_wizard_page(4)
        self.statusBar().showMessage(
            "به مرحله اجرا منتقل شدید. تنظیمات را بررسی و اجرا کنید.",
            3500,
        )

    def _export_from_normal(self) -> None:
        """Use the existing Step6 export behaviour."""
        if self.wizard.state.result is None:
            QMessageBox.warning(
                self,
                "نتیجه موجود نیست",
                "ابتدا تخصیص را اجرا کنید.",
            )
            self._open_wizard_page(4)
            return

        page_ids = self.wizard.pageIds()
        if len(page_ids) >= 6:
            self.wizard.setCurrentId(page_ids[5])

        self.stack.setCurrentWidget(self.wizard)

        try:
            self.wizard.s6.export()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(
                self,
                "خطا در خروجی",
                f"خروجی گرفتن ناموفق بود:\n{exc}",
            )

        self.refresh_shell_status()

    # ── status / help ───────────────────────────────────────────
    def refresh_shell_status(self) -> None:
        """Refresh MainWindow status labels from shared wizard state."""
        state = self.wizard.state

        is_normal = self.stack.currentWidget() is self.normal_workspace
        self.sb_mode.setText(
            "حالت: عادی" if is_normal else "حالت: ویزارد"
        )

        book1_ok = bool(state.book1_rows)
        book2_ok = bool(state.book2_rows)

        if book1_ok and book2_ok:
            files_text = "فایل‌ها: کامل"
        elif book1_ok or book2_ok:
            files_text = "فایل‌ها: ناقص"
        else:
            files_text = "فایل‌ها: بارگذاری نشده"

        self.sb_files.setText(files_text)
        self.sb_students.setText(
            f"دانش‌آموز: {len(state.book2_rows)}"
            if state.book2_rows else
            "دانش‌آموز: —"
        )
        self.sb_mentors.setText(
            f"پشتیبان: {len(state.book1_rows)}"
            if state.book1_rows else
            "پشتیبان: —"
        )

        if state.result is not None:
            self.sb_result.setText(
                f"نتیجه: {'تأییدشده' if state.result.approved_assignment_snapshot is not None else 'پیش‌نمایش'} · ظرفیت {state.result.capacity}"
            )
        else:
            self.sb_result.setText("نتیجه: —")

        if self.stack.currentWidget() is self.normal_workspace:
            self.normal_workspace.refresh()

    def _show_help(self) -> None:
        QMessageBox.information(
            self,
            "راهنمای میان‌برها",
            "میان‌برهای عمومی برنامه:\n\n"
            "Ctrl+1    حالت ویزارد\n"
            "Ctrl+2    حالت عادی / Workspace\n"
            "Ctrl+O    رفتن به بارگذاری فایل‌ها\n"
            "F5        رفتن به اجرای تخصیص\n"
            "Ctrl+S    خروجی گرفتن\n"
            "F1        نمایش این راهنما",
        )

    # ── persistence ─────────────────────────────────────────────
    def _restore_window_settings(self) -> None:
        """Restore geometry and last selected mode."""
        geo = self.settings.value("main_window_geometry")
        if geo:
            self.restoreGeometry(geo)

        last_mode = self.settings.value(
            "last_mode",
            self.MODE_WIZARD,
            int,
        )

        idx = self.mode_combo.findData(last_mode)
        if idx < 0:
            idx = self.mode_combo.findData(self.MODE_WIZARD)

        if idx >= 0:
            self.mode_combo.setCurrentIndex(idx)
            self._switch_mode_from_combo()

    def closeEvent(self, event):  # noqa: N802
        """Persist shell and wizard settings."""
        self.settings.setValue("main_window_geometry", self.saveGeometry())
        self.settings.setValue("last_mode", self.mode_combo.currentData())

        if hasattr(self.wizard, "_save_settings"):
            self.wizard._save_settings()  # noqa: SLF001

        super().closeEvent(event)
