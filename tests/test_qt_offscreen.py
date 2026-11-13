"""Actual PySide6 offscreen smoke for review -> final -> local export.

Offscreen is not Windows operator acceptance; it exercises real Qt widgets,
synchronous confirmation and workbook output.
"""
import gc

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication

from app.ui.pages.step4_preview import Step4Preview
from app.ui.pages.step5_execute import Step5Execute
from app.ui.pages.step6_export import Step6Export
from tests.test_allocation_path import make_state


# QApplication must outlive Qt widgets in their C++ lifetime.
_APP = QApplication.instance() or QApplication([])


def test_qt_preview_execution_export(monkeypatch, tmp_path):
    app = _APP
    state = make_state(121, 60)
    preview = Step4Preview(state)
    preview.initializePage()
    assert preview.isComplete()
    before_manual = state.result.assignment_snapshot()
    moved_student = state.result.assigned["M000"][-1]
    preview._on_move(moved_student, "M000", "M001")
    after_manual = state.result.assignment_snapshot()
    assert after_manual != before_manual
    assert preview.validatePage()
    preview.undo_stack.undo()
    assert state.result.assignment_snapshot() == before_manual
    preview.undo_stack.redo()
    assert state.result.assignment_snapshot() == after_manual
    assert preview.validatePage()

    initial = state.result.assignment_snapshot()
    run = Step5Execute(state)
    monkeypatch.setattr(
        "app.ui.pages.step5_execute.ConfirmExecutionDialog.confirm",
        lambda *args: True,
    )
    run.initializePage()
    assert not run.isComplete()
    assert not hasattr(run, "_worker")
    assert not hasattr(run, "stop_btn")
    assert not hasattr(run, "pbar")
    run.start()
    app.processEvents()
    assert run.isComplete()
    assert state.result.assignment_snapshot() == initial
    assert state.result.approved_assignment_snapshot is not None

    export = Step6Export(state)
    export.path.setText(str(tmp_path / "final.xlsx"))
    export.export()
    assert (tmp_path / "final.xlsx").exists()
    assert not (tmp_path / "final_report.html").exists()
    from openpyxl import load_workbook
    workbook = load_workbook(tmp_path / "final.xlsx", data_only=True)
    assert workbook.active.cell(row=moved_student + 2, column=7).value == "M001"
    workbook.close()

    for widget in (preview, run, export):
        widget.close()
        widget.deleteLater()
    # Drain C++ deletion events before leaving the QApplication instance.
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()
    del preview, run, export
    gc.collect()


def test_real_six_step_main_window_initializes_offscreen():
    """Prove the application's real main-window composition can initialize."""
    from app.ui.main_window import MainWindow
    app = _APP
    window = MainWindow()
    assert len(window.wizard.pageIds()) == 6
    assert window.wizard.state.result is None
    app.processEvents()
    window.close()
    window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()


def _approved_synthetic_state():
    from app.services.allocation_service import allocate

    state = make_state(6, 3)
    state.result = allocate(state)
    state.result_input_signature = state.input_signature()
    state.result.mark_approved()
    return state


def test_excel_only_overwrite_leaves_legacy_html_untouched(monkeypatch, tmp_path):
    from types import SimpleNamespace
    from openpyxl import load_workbook
    from app.ui.pages import step6_export

    state = _approved_synthetic_state()
    path = tmp_path / "final.xlsx"
    path.write_bytes(b"previous workbook")
    legacy_html = tmp_path / "final_report.html"
    legacy_html.write_text("previous HTML from earlier version", encoding="utf-8")
    page = Step6Export(state)
    page.path.setText(str(path))
    confirmation = SimpleNamespace(
        StandardButton=SimpleNamespace(Yes=1, No=2),
        warning=lambda *args: 1,
    )
    monkeypatch.setattr(step6_export, "QMessageBox", confirmation)
    original_replace = step6_export.os.replace
    publications = []

    def record_replace(src, dst):
        publications.append(dst)
        return original_replace(src, dst)

    monkeypatch.setattr(step6_export.os, "replace", record_replace)
    page.export()
    assert publications == [path]
    workbook = load_workbook(path)
    assert workbook.active.max_row == 7
    workbook.close()
    assert legacy_html.read_text(encoding="utf-8") == "previous HTML from earlier version"
    assert "HTML" not in page.summary.text()
    assert set(tmp_path.iterdir()) == {path, legacy_html}
    page.close()
    page.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    _APP.processEvents()


def test_excel_only_replace_failure_preserves_previous_workbook(monkeypatch, tmp_path):
    from types import SimpleNamespace
    from app.ui.pages import step6_export

    state = _approved_synthetic_state()
    path = tmp_path / "final.xlsx"
    previous = b"previous workbook remains byte-for-byte unchanged"
    path.write_bytes(previous)
    page = Step6Export(state)
    page.path.setText(str(path))
    confirmation = SimpleNamespace(
        StandardButton=SimpleNamespace(Yes=1, No=2),
        warning=lambda *args: 1,
    )
    monkeypatch.setattr(step6_export, "QMessageBox", confirmation)
    calls = []

    def fail_publication(src, dst):
        calls.append(dst)
        raise PermissionError("synthetic replace failure")

    monkeypatch.setattr(step6_export.os, "replace", fail_publication)
    page.export()
    assert calls == [path]
    assert path.read_bytes() == previous
    assert not (tmp_path / "final_report.html").exists()
    assert set(tmp_path.iterdir()) == {path}
    assert "خطا در خروجی" in page.summary.text()
    assert not page.open_btn.isEnabled()
    page.close()
    page.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    _APP.processEvents()
