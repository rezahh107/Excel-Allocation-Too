"""Main wizard window — status bar (C1), tooltips (C2),
toast (C3), geometry persistence (C4), QSettings, project save/load."""
from __future__ import annotations

import json
import os
from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QWidget,
    QWizard,
)

from app.core.models import FairnessMode, Role, WizardState
from app.ui.pages.step1_load import Step1Load
from app.ui.pages.step2_mapping import Step2Mapping
from app.ui.pages.step3_settings import Step3Settings
from app.ui.pages.step4_preview import Step4Preview
from app.ui.pages.step5_execute import Step5Execute
from app.ui.pages.step6_export import Step6Export
from app.ui.widgets.toast import Toast
from app.utils.logger import get_logger
from app.utils.rtl_utils import apply_rtl
from app.utils.theme import ColorPalette as P

log = get_logger("wizard")

_ORG = "ClaudeOpus"
_APP = "ExcelAllocationTool"

# Safe enum fallback for older PySide6 versions vs new
try:
    _CB1 = QWizard.WizardButton.CustomButton1.value
    _CB2 = QWizard.WizardButton.CustomButton2.value
except AttributeError:
    _CB1, _CB2 = 6, 7


class _Divider(QFrame):
    """Thin vertical separator for the status bar."""

    def __init__(self) -> None:
        super().__init__()
        self.setFrameShape(QFrame.Shape.VLine)
        self.setFixedWidth(1)
        self.setStyleSheet(f"color:{P.SEPARATOR}")


class AllocationWizard(QWizard):
    """Six-step student-mentor allocation wizard."""

    PROJECT_FILTER = "Excel Allocation Project (*.eaproj.json);;JSON (*.json)"

    def __init__(self) -> None:
        super().__init__()
        apply_rtl(self)
        self.setWindowTitle("سامانه تخصیص پشتیبان  ·  v3.0")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.resize(1020, 780)
        self.setOption(QWizard.WizardOption.IndependentPages, False)
        self.setOption(QWizard.WizardOption.HaveHelpButton, True)
        self.setOption(QWizard.WizardOption.HaveCustomButton1, True)
        self.setOption(QWizard.WizardOption.HaveCustomButton2, True)

        self.settings = QSettings(_ORG, _APP)
        self.state = WizardState()
        self._load_settings()

        self.s1 = Step1Load(self.state)
        self.s2 = Step2Mapping(self.state)
        self.s3 = Step3Settings(self.state)
        self.s4 = Step4Preview(self.state)
        self.s5 = Step5Execute(self.state)
        self.s6 = Step6Export(self.state)
        for page in (self.s1, self.s2, self.s3, self.s4, self.s5, self.s6):
            self.addPage(page)

        self.setButtonText(QWizard.WizardButton.CustomButton1, "📂 باز کردن پروژه")
        self.setButtonText(QWizard.WizardButton.CustomButton2, "💾 ذخیره پروژه")

        self.toast = Toast(self)
        self._build_status_bar()
        self._setup_shortcuts()

        self.currentIdChanged.connect(self._on_page_changed)
        self.helpRequested.connect(self._show_help)
        self.finished.connect(self._save_settings)
        self.customButtonClicked.connect(self._on_custom_button_clicked)

        geo = self.settings.value("geometry")
        if geo:
            self.restoreGeometry(geo)

        self.s1.restore_paths()
        self.refresh_status()

    def setCurrentId(self, page_id: int) -> None:  # noqa: N802
        """Guard direct Python requests for the protected export page."""
        ids = self.pageIds()
        if len(ids) >= 6 and page_id == ids[5] and not self.state.export_eligible():
            self._leave_invalid_export()
            if hasattr(self, "toast"):
                self.toast.show_message(
                    "خروجی نیازمند پیش‌نمایش و تأیید معتبر است.", "warning"
                )
            return
        # Qt setCurrentId validates even when navigating BACK. An unapproved
        # Step 5 must not trap the user there; native back() safely unwinds
        # already visited pages without treating navigation as confirmation.
        if (len(ids) >= 5 and self.currentId() == ids[4]
                and page_id < ids[4] and self.hasVisitedPage(page_id)
                and not self.state.export_eligible()):
            while self.currentId() != page_id:
                previous_id = self.currentId()
                self.back()
                if self.currentId() == previous_id:
                    break
            if self.currentId() == page_id:
                return
        super().setCurrentId(page_id)

    def _leave_invalid_export(self) -> None:
        """Protect native Qt transitions that bypass Python navigation callers."""
        ids = self.pageIds()
        if len(ids) < 6 or self.currentId() != ids[5]:
            return
        if self.state.export_eligible():
            return
        fallback = ids[3] if self.state.result is not None else ids[0]
        # setCurrentId() moves backward without unwinding Qt's visited history;
        # next() then rejects the old Step 5 as an "already met" page.
        # Use native Back until the last reviewed page; if it was never
        # visited (direct Step 6 jump), recover to the first visited page.
        history = self.visitedIds()
        if fallback not in history:
            fallback = history[0]
        while self.currentId() != fallback and len(self.visitedIds()) > 1:
            previous = self.currentId()
            self.back()
            if self.currentId() == previous:
                break
        if hasattr(self, "toast"):
            self.toast.show_message(
                "تأیید خروجی نامعتبر است؛ پیش‌نمایش را بررسی کنید.", "warning"
            )

    # ── status bar (C1) ─────────────────────────────────────────
    def _build_status_bar(self) -> None:
        self._sb_students = QLabel("دانش‌آموز: —")
        self._sb_mentors = QLabel("پشتیبان: —")
        self._sb_capacity = QLabel("ظرفیت: —")
        self._sb_mode = QLabel("حالت: —")
        self._sb_state = QLabel("⏳ در انتظار فایل")

        bar_widget = QWidget()
        bar_widget.setObjectName("statusBar")
        bar_widget.setStyleSheet(
            f"""
            QWidget#statusBar {{
                background-color: {P.BG_SURFACE};
                border: 0;
                border-top: 1px solid {P.BORDER};
            }}
            QWidget#statusBar QLabel {{
                color: {P.TEXT_MUTED};
                padding: 3px 8px;
                font-size: 12px;
                background: transparent;
                border: 0;
            }}
            """
        )
        h = QHBoxLayout(bar_widget)
        h.setContentsMargins(8, 2, 8, 2)
        h.setSpacing(0)
        for lbl in (
            self._sb_students,
            self._sb_mentors,
            self._sb_capacity,
            self._sb_mode,
            self._sb_state,
        ):
            h.addWidget(lbl)
            h.addWidget(_Divider())
        h.addStretch()

        main_layout = self.layout()
        if main_layout:
            main_layout.addWidget(bar_widget)
        self._status_bar_widget = bar_widget

    def refresh_status(self) -> None:
        s = self.state
        if hasattr(self, "s6"):
            self.s6.refresh_eligibility()
            self._leave_invalid_export()
        self._sb_students.setText(
            f"دانش‌آموز: {len(s.book2_rows)}" if s.book2_rows else "دانش‌آموز: —"
        )
        self._sb_mentors.setText(
            f"پشتیبان: {len(s.book1_rows)}" if s.book1_rows else "پشتیبان: —"
        )

        if s.result:
            self._sb_capacity.setText(f"ظرفیت: {s.result.capacity}")
            self._sb_state.setText("✅  آماده خروجی" if s.export_eligible() else "⏳ در انتظار تأیید")
            self._sb_state.setStyleSheet(
                f"color:{P.SUCCESS_LIGHT};font-weight:bold;padding:3px 8px;font-size:12px;"
            )
        elif s.book1_rows and s.book2_rows:
            self._sb_capacity.setText(
                f"ظرفیت: {s.capacity_override}" if s.capacity_override else "ظرفیت: خودکار"
            )
            self._sb_state.setText("✅  فایل‌ها بارگذاری شدند")
            self._sb_state.setStyleSheet(
                f"color:{P.SUCCESS_LIGHT};padding:3px 8px;font-size:12px;"
            )
        else:
            self._sb_capacity.setText("ظرفیت: —")
            self._sb_state.setText("⏳  در انتظار فایل")
            self._sb_state.setStyleSheet(
                f"color:{P.TEXT_MUTED};padding:3px 8px;font-size:12px;"
            )

        self._sb_mode.setText(f"حالت: {s.fairness.value}")

    # ── smart tooltip on Next (C2) ──────────────────────────────
    def _on_page_changed(self, page_id: int) -> None:
        ids = self.pageIds()
        if len(ids) >= 6 and page_id == ids[5] and not self.state.export_eligible():
            # Step 6 disables actions synchronously; leave it after Qt's signal.
            QTimer.singleShot(0, self._leave_invalid_export)
        page = self.currentPage()
        next_btn = self.button(QWizard.WizardButton.NextButton)
        if next_btn is None or page is None:
            return
        if not page.isComplete():
            reason = getattr(
                page,
                "incomplete_reason",
                lambda: "این مرحله هنوز کامل نشده است",
            )()
            next_btn.setToolTip(f"⚠  {reason}")
        else:
            next_btn.setToolTip("")
        if hasattr(self, "toast"):
            self.toast.hide()

    # ── shortcuts ───────────────────────────────────────────────
    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+O"), self, lambda: self.setCurrentId(self.pageIds()[0]))
        QShortcut(QKeySequence("Ctrl+S"), self, self._global_export)
        QShortcut(QKeySequence("Ctrl+Shift+O"), self, self.open_project)
        QShortcut(QKeySequence("Ctrl+Shift+S"), self, self.save_project)
        QShortcut(QKeySequence("Ctrl+Z"), self, self._safe_undo)
        QShortcut(QKeySequence("Ctrl+Y"), self, self._safe_redo)
        QShortcut(QKeySequence("F1"), self, self._show_help)

    def _safe_undo(self) -> None:
        stack = getattr(self.s4, "undo_stack", None)
        if stack is not None and hasattr(stack, "undo"):
            try:
                stack.undo()
            except Exception as exc:
                log.debug("undo ناموفق بود: %s", exc)

    def _safe_redo(self) -> None:
        stack = getattr(self.s4, "undo_stack", None)
        if stack is not None and hasattr(stack, "redo"):
            try:
                stack.redo()
            except Exception as exc:
                log.debug("redo ناموفق بود: %s", exc)

    def _on_custom_button_clicked(self, which: int) -> None:
        if which == _CB1:
            self.open_project()
        elif which == _CB2:
            self.save_project()

    def _global_export(self) -> None:
        if not self.state.export_eligible():
            self.toast.show_message("ابتدا پیش‌نمایش را بررسی و تخصیص را تأیید کنید.", "warning")
            return
        self.s6.export()

    def _show_help(self) -> None:
        QMessageBox.information(
            self,
            "راهنما",
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  Ctrl+O         بارگذاری فایل‌ها (مرحله ۱)\n"
            "  Ctrl+S         خروجی گرفتن (از هر صفحه)\n"
            "  Ctrl+Shift+O   باز کردن پروژه\n"
            "  Ctrl+Shift+S   ذخیره پروژه\n"
            "  Ctrl+Z         واگرد (مرحله ۴)\n"
            "  Ctrl+Y         ازنو  (مرحله ۴)\n"
            "  F1             این راهنما\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━"
        )

    # ── project save/load (C5) ──────────────────────────────────
    def save_project(self) -> None:
        """Save current wizard working state to a JSON project file atomically."""
        suggested = self._default_project_path()
        path, _ = QFileDialog.getSaveFileName(
            self, "ذخیره پروژه", suggested, self.PROJECT_FILTER
        )
        if not path:
            return

        path = self._normalise_project_path(path)
        payload = self._build_project_payload()

        try:
            tmp_path = path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
            
            os.replace(tmp_path, path)

            self.settings.setValue("last_project_path", path)
            self.toast.show_message("پروژه ذخیره شد.", "success")
            log.info("پروژه ذخیره شد: %s", path)
        except Exception as exc:
            log.exception("خطا در ذخیره پروژه: %s", exc)
            QMessageBox.critical(
                self, "خطا در ذخیره پروژه", f"ذخیره پروژه ناموفق بود:\n{exc}"
            )

    def open_project(self) -> None:
        """Open a previously saved project JSON file."""
        if self._has_meaningful_state():
            reply = QMessageBox.question(
                self,
                "باز کردن پروژه",
                "وضعیت فعلی جایگزین خواهد شد. ادامه می‌دهید؟",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        start_dir = self.settings.value(
            "last_project_path", self._default_project_path(), str
        )
        path, _ = QFileDialog.getOpenFileName(
            self, "باز کردن پروژه", start_dir, self.PROJECT_FILTER
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)

            if not isinstance(data, dict):
                raise ValueError("ساختار فایل پروژه معتبر نیست.")

            version = self._project_version(data)
            if version > 2:
                log.warning("نسخه فایل پروژه جدیدتر از این برنامه است: %s", version)
            elif version < 1:
                raise ValueError("نسخه فایل پروژه معتبر نیست.")

            self._apply_project_payload(data)
            self.settings.setValue("last_project_path", path)
            self.toast.show_message("پروژه بارگذاری شد.", "success")
            log.info("پروژه بارگذاری شد: %s", path)
        except Exception as exc:
            log.exception("خطا در باز کردن پروژه: %s", exc)
            QMessageBox.critical(
                self, "خطا در باز کردن پروژه", f"بارگذاری پروژه ناموفق بود:\n{exc}"
            )

    def _build_project_payload(self) -> dict:
        current_step_index = 0
        try:
            current_step_index = self.pageIds().index(self.currentId())
        except ValueError:
            current_step_index = 0

        return {
            "version": 2,
            "book1_path": self.state.book1_path,
            "book2_path": self.state.book2_path,
            "map1": self._encode_role_map(self.state.map1),
            "map2": self._encode_role_map(self.state.map2),
            "fairness": self.state.fairness.value,
            "capacity_override": self.state.capacity_override,
            "stabilize_initial": bool(self.state.stabilize_initial),
            "current_step_index": current_step_index,
        }

    def _apply_project_payload(self, data: dict) -> None:
        self.state.book1_path = str(data.get("book1_path", "") or "")
        self.state.book2_path = str(data.get("book2_path", "") or "")

        raw_map1 = data.get("map1", {})
        raw_map2 = data.get("map2", {})
        self.state.map1 = self._decode_role_map(raw_map1 if isinstance(raw_map1, dict) else {})
        self.state.map2 = self._decode_role_map(raw_map2 if isinstance(raw_map2, dict) else {})

        # Restore backwards compatibility for _load_settings flow
        if hasattr(self.state, "saved_map1"):
            self.state.saved_map1 = raw_map1 if isinstance(raw_map1, dict) else {}
        if hasattr(self.state, "saved_map2"):
            self.state.saved_map2 = raw_map2 if isinstance(raw_map2, dict) else {}

        fairness_value = str(data.get("fairness", FairnessMode.ROUND_ROBIN.value) or "")
        try:
            self.state.fairness = FairnessMode(fairness_value)
        except ValueError:
            self.state.fairness = FairnessMode.ROUND_ROBIN

        cap = data.get("capacity_override", None)
        if cap in ("", None):
            self.state.capacity_override = None
        else:
            try:
                self.state.capacity_override = int(cap)
            except (TypeError, ValueError):
                self.state.capacity_override = None

        self.state.stabilize_initial = bool(data.get("stabilize_initial", True))
        self.state.invalidate_result()
        self.state.map_errors = []

        self._reload_rows_from_paths()
        self._sync_pages_from_state()
        self.refresh_status()

        step_index = data.get("current_step_index", 0)
        try:
            step_index = int(step_index)
        except (TypeError, ValueError):
            step_index = 0

        page_ids = self.pageIds()
        if 0 <= step_index < len(page_ids):
            try:
                self.setCurrentId(page_ids[step_index])
            except Exception as exc:
                log.debug("عدم امکان رفتن به مرحله ذخیره‌شده: %s", exc)

    def _reload_rows_from_paths(self) -> None:
        try:
            from app.services.excel_service import load_table
        except Exception as exc:
            log.warning("load_table در دسترس نیست: %s", exc)
            self.state.book1_rows = []
            self.state.book2_rows = []
            return

        warnings: list[str] = []

        def _load(path: str, label: str) -> list[dict]:
            if not path:
                return []
            try:
                headers, rows = load_table(path)
                if label == "Book1":
                    self.state.book1_headers = headers
                else:
                    self.state.book2_headers = headers
                return rows
            except Exception as exc:
                warnings.append(f"{label}: {exc}")
                return []

        self.state.book1_rows = _load(self.state.book1_path, "Book1")
        self.state.book2_rows = _load(self.state.book2_path, "Book2")

        if warnings:
            self.toast.show_message("بخشی از فایل‌های پروژه بارگذاری نشدند.", "warning")

    def _sync_pages_from_state(self) -> None:
        try:
            if hasattr(self.s1, "restore_paths"):
                self.s1.restore_paths()
        except Exception as exc:
            log.debug("restore_paths ناموفق بود: %s", exc)

        try:
            if hasattr(self.s3, "sync_from_state"):
                self.s3.sync_from_state()
            else:
                idx = self.s3.fairness_combo.findData(self.state.fairness)
                if idx >= 0:
                    self.s3.fairness_combo.setCurrentIndex(idx)

                is_auto = self.state.capacity_override is None
                self.s3.auto_capacity.setChecked(is_auto)

                if self.state.capacity_override is not None:
                    self.s3.capacity_spin.setValue(self.state.capacity_override)

                self.s3.capacity_spin.setEnabled(not is_auto)
                self.s3.stabilize_chk.setChecked(self.state.stabilize_initial)

                if hasattr(self.s3, "_update_fairness_desc"):
                    self.s3._update_fairness_desc()
                if hasattr(self.s3, "_refresh_dashboard"):
                    self.s3._refresh_dashboard()
        except Exception as exc:
            log.debug("همگام‌سازی Step3 ناموفق بود: %s", exc)

        for page in (self.s2, self.s4, self.s5, self.s6):
            try:
                page.completeChanged.emit()
            except Exception:
                pass

    def _default_project_path(self) -> str:
        last_book = self.state.book2_path or self.state.book1_path
        if not last_book:
            return "allocation_project.eaproj.json"
        p = Path(last_book)
        return str(p.with_name(f"{p.stem}.eaproj.json"))

    @staticmethod
    def _normalise_project_path(path: str) -> str:
        p = Path(path)
        if not p.name.lower().endswith(".eaproj.json"):
            return str(p.with_name(f"{p.stem}.eaproj.json"))
        return str(p)

    @staticmethod
    def _project_version(data: dict) -> int:
        try:
            return int(data.get("version", 1))
        except (TypeError, ValueError):
            return 1

    def _has_meaningful_state(self) -> bool:
        return any(
            [
                bool(self.state.book1_path),
                bool(self.state.book2_path),
                bool(self.state.book1_rows),
                bool(self.state.book2_rows),
                bool(self.state.map1),
                bool(self.state.map2),
                self.state.result is not None,
            ]
        )

    @staticmethod
    def _encode_role_map(data: dict) -> dict[str, str]:
        out: dict[str, str] = {}
        for col, role in (data or {}).items():
            key = str(col)
            try:
                out[key] = role.value
            except Exception:
                out[key] = str(role)
        return out

    @staticmethod
    def _decode_role_map(data: dict) -> dict[str, Role]:
        out: dict[str, Role] = {}
        if not isinstance(data, dict):
            return out
        for col, raw in data.items():
            try:
                out[str(col)] = Role(str(raw))
            except ValueError:
                continue
        return out

    # ── resize toast on window resize ───────────────────────────
    def resizeEvent(self, e):  # noqa: N802
        super().resizeEvent(e)
        if hasattr(self, "toast") and self.toast.isVisible():
            x = self.width() - self.toast.width() - 20
            y = self.height() - self.toast.height() - 55
            self.toast.move(x, y)

    # ── QSettings persistence ────────────────────────────────────
    def _load_settings(self) -> None:
        self.state.book1_path = self.settings.value("last_book1", "", str)
        self.state.book2_path = self.settings.value("last_book2", "", str)
        
        raw_map1 = self._load_json("map1_json")
        raw_map2 = self._load_json("map2_json")
        self.state.map1 = self._decode_role_map(raw_map1)
        self.state.map2 = self._decode_role_map(raw_map2)
        
        # Backward compatibility for the original attributes
        if hasattr(self.state, "saved_map1"):
            self.state.saved_map1 = raw_map1
        if hasattr(self.state, "saved_map2"):
            self.state.saved_map2 = raw_map2

        mode = self.settings.value("fairness", FairnessMode.ROUND_ROBIN.value, str)
        try:
            self.state.fairness = FairnessMode(mode)
        except ValueError:
            self.state.fairness = FairnessMode.ROUND_ROBIN
        log.info("تنظیمات بارگذاری شد.")

    def _load_json(self, key: str) -> dict[str, str]:
        raw = self.settings.value(key, "", str)
        if not raw:
            return {}
        try:
            return dict(json.loads(raw))
        except (ValueError, TypeError):
            return {}

    def _save_settings(self) -> None:
        self.settings.setValue("last_book1", self.state.book1_path)
        self.settings.setValue("last_book2", self.state.book2_path)
        self.settings.setValue(
            "map1_json",
            json.dumps(
                {c: r.value for c, r in self.state.map1.items()}, ensure_ascii=False
            ),
        )
        self.settings.setValue(
            "map2_json",
            json.dumps(
                {c: r.value for c, r in self.state.map2.items()}, ensure_ascii=False
            ),
        )
        self.settings.setValue("fairness", self.state.fairness.value)
        self.settings.setValue("geometry", self.saveGeometry())
        log.info("تنظیمات ذخیره شد.")
