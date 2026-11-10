"""Actual PySide6 offscreen smoke for review -> final -> local export.

Offscreen is not Windows operator acceptance; it does exercise real Qt signals,
page constructors, the worker and the workbook output.
"""
import time
import gc

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication

from app.ui.pages.step4_preview import Step4Preview
from app.ui.pages.step5_execute import Step5Execute
from app.ui.pages.step6_export import Step6Export
from tests.test_allocation_path import make_state


# QApplication must outlive all widgets and the QThread in Qt's C++ lifetime.
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
    run.start()
    deadline = time.monotonic() + 10
    while not run.isComplete() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)
    app.processEvents()
    assert run.isComplete(), run.log.toPlainText() if hasattr(run.log, "toPlainText") else "worker not completed"
    assert run._worker is not None and run._worker.wait(3000)
    assert state.result.assignment_snapshot() == initial
    assert state.result.approved_assignment_snapshot is not None

    export = Step6Export(state)
    export.path.setText(str(tmp_path / "final.xlsx"))
    export.export()
    assert (tmp_path / "final.xlsx").exists()
    assert (tmp_path / "final_report.html").exists()
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
