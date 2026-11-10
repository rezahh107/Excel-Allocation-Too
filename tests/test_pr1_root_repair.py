"""Synthetic negative and positive controls for Excel-only, movement and manual-capacity rules."""
from __future__ import annotations


import pytest
from openpyxl import load_workbook
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtGui import QColor

from app.core.models import Role
from app.core.validation import ValidationError, ensure_reassignment_admissible, validate_result
from app.services.allocation_service import allocate
from app.services.excel_service import export_excel
from app.ui.pages.step4_preview import Step4Preview
from app.ui.pages.step6_export import Step6Export
from app.ui.widgets.allocation_tree import ROLE_STUDENT_IDX
from app.utils.theme import ColorPalette as P
from tests.test_allocation_path import make_state
from tests.test_qt_offscreen import _APP


def _approved_state(n=6, k=3):
    state = make_state(n, k)
    state.result = allocate(state)
    state.result_input_signature = state.input_signature()
    state.result.mark_approved()
    return state


def _dispose(widget):
    widget.close()
    widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    _APP.processEvents()


def test_truthful_movement_new_unchanged_changed_and_normalized():
    state = make_state(6, 3)
    state.book2_rows[0]["previous"] = " m000 "
    state.book2_rows[1]["previous"] = "M999"  # nonempty imported label differs
    result = allocate(state)
    assert result.mentor_for_student(0) == "M000"
    assert result.movement_counts() == {"new": 4, "unchanged": 1, "changed": 1}
    assert result.num_moved == 1
    assert result.num_non_stabilized == 6  # independent of actual movement

    state.stabilize_initial = True
    state.book2_rows[1]["previous"] = "M000"
    result = allocate(state)
    assert result.movement_counts()["new"] == 4
    assert result.movement_counts()["unchanged"] >= 1
    assert result.num_moved == result.movement_counts()["changed"]


def test_movement_tracks_manual_reassignment_and_undo_redo():
    state = make_state(121, 60)
    state.book2_rows[0]["previous"] = "M000"
    preview = Step4Preview(state)
    preview.initializePage()
    assert state.result.num_moved == 0
    assert preview.validatePage()
    preview._on_move(0, "M000", "M001")
    assert state.result.num_moved == 1
    assert state.result.num_non_stabilized == 121
    assert not state.preview_reviewed
    assert preview.validatePage()
    preview.undo_stack.undo()
    assert state.result.num_moved == 0
    preview.undo_stack.redo()
    assert state.result.num_moved == 1
    _dispose(preview)


def test_excel_stats_use_final_assignment_not_stabilization(tmp_path):
    state = make_state(6, 3)
    state.book2_rows[0]["previous"] = "M000"
    state.book2_rows[1]["previous"] = "M999"
    result = allocate(state)
    result.mark_approved()
    output = tmp_path / "out.xlsx"
    export_excel(result, {m.name: m.manager for m in result.mentors}, str(output))
    wb = load_workbook(output, data_only=True)
    statistics = dict(list(wb["گزارش آماری"].values)[1:])
    assert statistics["تعداد جابه‌جا شده"] == 1
    assert statistics["تعداد تخصیص جدید (بدون پشتیبان اولیه)"] == 4
    assert statistics["تعداد تثبیت‌نشده"] == 6
    assert statistics["تعداد بدون تغییر پشتیبان"] == 1
    assert wb.worksheets[0].max_row == 7
    wb.close()


def test_zero_capacity_move_rejected_without_undo_or_review_change():
    state = make_state(3, 8)
    state.map1["cap"] = Role.CAPACITY
    for index, row in enumerate(state.book1_rows):
        row["cap"] = "1" if index < 3 else "0"
    page = Step4Preview(state)
    page.initializePage()
    assert page.validatePage()
    state.result.mark_approved()
    before = state.result.assignment_snapshot()
    approved = state.result.approved_assignment_snapshot
    idx = state.result.assigned["M000"][0]
    page._on_move(idx, "M000", "M003")
    assert state.result.assignment_snapshot() == before
    assert page.undo_stack.count() == 0
    assert state.preview_reviewed
    assert state.result.approved_assignment_snapshot == approved
    assert state.result.mentor_capacity("M003") == 0
    assert "ظرفیت" in page.info.text()
    _dispose(page)



def test_zero_capacity_target_is_shown_full_and_highlighted_red():
    state = make_state(3, 8)
    state.map1["cap"] = Role.CAPACITY
    for index, row in enumerate(state.book1_rows):
        row["cap"] = "1" if index < 3 else "0"
    page = Step4Preview(state)
    page.initializePage()
    zero = page.tree._mentor_items["M003"]
    assert "0/0" in zero.text(2)
    source_item = page.tree._mentor_items["M000"].child(0)
    page.tree.setCurrentItem(source_item)
    page.tree._highlight_targets()
    assert zero.background(0).color() == QColor(P.ERROR + "44")
    _dispose(page)


def test_stricter_per_mentor_capacity_and_unknown_destination():
    state = make_state(5, 3)
    state.map1["cap"] = Role.CAPACITY
    for index, row in enumerate(state.book1_rows):
        row["cap"] = "2" if index < 2 else "1"
    result = allocate(state)
    assert result.capacity == 2 and result.mentor_capacity("M002") == 1
    source = result.assigned["M000"][0]
    with pytest.raises(ValidationError, match="ظرفیت"):
        ensure_reassignment_admissible(result, source, "M000", "M002")
    with pytest.raises(ValidationError, match="وجود ندارد"):
        ensure_reassignment_admissible(result, source, "M000", "UNKNOWN")
    with pytest.raises(ValidationError, match="مبدا"):
        ensure_reassignment_admissible(result, source, "M001", "M000")
    with pytest.raises(ValidationError, match="شناسه"):
        ensure_reassignment_admissible(result, True, "M000", "M001")


def test_drag_highlighting_uses_the_same_admission_rule():
    state = make_state(121, 60)
    page = Step4Preview(state)
    page.initializePage()
    source_item = page.tree._mentor_items["M000"].child(0)
    assert source_item.data(0, ROLE_STUDENT_IDX) is not None
    page.tree.setCurrentItem(source_item)
    page.tree._highlight_targets()
    assert page.tree._mentor_items["M001"].background(0).color() == QColor(P.SUCCESS + "44")
    assert page.tree._mentor_items["M000"].background(0).color() == QColor(P.ERROR + "44")
    _dispose(page)


def test_global_fairness_remains_final_authority():
    result = allocate(make_state(121, 60))
    i = result.assigned["M001"].pop()
    result.assigned["M002"].append(i)
    assert "global_mentor_fairness" in validate_result(result)[0]


def test_stabilized_move_is_not_admitted():
    state = make_state(121, 60, concentrated=True)
    result = allocate(state)
    student_idx = next(iter(result.stabilized))
    with pytest.raises(ValidationError, match="تثبیت"):
        ensure_reassignment_admissible(result, student_idx, "M000", "M001")


def test_stale_html_warning_survives_success_and_preserves_bytes(tmp_path):
    state = _approved_state()
    excel = tmp_path / "final.xlsx"
    legacy = tmp_path / "final_report.html"
    original = b"<html>Historical file: DO NOT TOUCH</html>\x00"
    legacy.write_bytes(original)
    page = Step6Export(state)
    page.path.setText(str(excel))
    page.show()
    _APP.processEvents()
    assert "قدیمی" in page.legacy_warning.text()
    assert "نباید" in page.legacy_warning.text()
    assert page.legacy_warning.isVisible()
    page.export()
    assert excel.is_file()
    assert legacy.read_bytes() == original
    assert "فایل اکسل" in page.summary.text()
    assert "HTML" not in page.summary.text()
    assert "قدیمی" in page.legacy_warning.text()
    assert page.legacy_warning.isVisible()
    page.path.setText(str(tmp_path / "different.xlsx"))
    assert not page.legacy_warning.text()
    _dispose(page)


def test_replace_failure_retains_old_excel_and_legacy_warning(tmp_path, monkeypatch):
    from app.ui.pages import step6_export

    state = _approved_state()
    excel = tmp_path / "final.xlsx"
    excel.write_bytes(b"old excel (synthetic)")
    legacy = tmp_path / "final_report.html"
    legacy.write_bytes(b"old HTML (synthetic)")
    page = Step6Export(state)
    page.path.setText(str(excel))
    from types import SimpleNamespace
    confirmation = SimpleNamespace(
        StandardButton=SimpleNamespace(Yes=1, No=2),
        warning=lambda *args: 1,
    )
    monkeypatch.setattr(step6_export, "QMessageBox", confirmation)
    calls = []

    def reject_replace(src, dest):
        calls.append(dest)
        raise PermissionError("simulated permission denial")

    monkeypatch.setattr(step6_export.os, "replace", reject_replace)
    page.export()
    assert calls == [excel]
    assert excel.read_bytes() == b"old excel (synthetic)"
    assert legacy.read_bytes() == b"old HTML (synthetic)"
    assert "خطا در خروجی" in page.summary.text()
    assert "قدیمی" in page.legacy_warning.text()
    assert not page.open_btn.isEnabled()
    _dispose(page)


def test_stale_input_during_excel_staging_prevents_publication(tmp_path, monkeypatch):
    from app.ui.pages import step6_export

    state = _approved_state()
    excel = tmp_path / "final.xlsx"
    previous = b"previous workbook"
    excel.write_bytes(previous)
    page = Step6Export(state)
    page.path.setText(str(excel))
    from types import SimpleNamespace
    confirmation = SimpleNamespace(
        StandardButton=SimpleNamespace(Yes=1, No=2),
        warning=lambda *args: 1,
    )
    monkeypatch.setattr(step6_export, "QMessageBox", confirmation)
    authentic_export = step6_export.export_excel

    def change_input_after_stage(*args, **kwargs):
        authentic_export(*args, **kwargs)
        state.book2_rows[0]["first"] = "changed after staging"

    monkeypatch.setattr(step6_export, "export_excel", change_input_after_stage)
    page.export()
    assert excel.read_bytes() == previous
    assert "خطا در خروجی" in page.summary.text()
    _dispose(page)
