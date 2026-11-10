"""Actual PySide6 offscreen smoke for review -> final -> local export.

Offscreen is not Windows operator acceptance; it does exercise real Qt signals,
page constructors, the worker and the workbook output.
"""
import time

from PySide6.QtWidgets import QApplication

from app.ui.pages.step4_preview import Step4Preview
from app.ui.pages.step5_execute import Step5Execute
from app.ui.pages.step6_export import Step6Export
from tests.test_allocation_path import make_state


def test_qt_preview_execution_export(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    state = make_state(121, 60)
    preview = Step4Preview(state)
    preview.initializePage()
    assert preview.isComplete()
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
    assert state.result.assignment_snapshot() == initial
    assert state.result.approved_assignment_snapshot is not None

    export = Step6Export(state)
    export.path.setText(str(tmp_path / "final.xlsx"))
    export.export()
    assert (tmp_path / "final.xlsx").exists()
    assert (tmp_path / "final_report.html").exists()

    preview.close()
    run.close()
    export.close()
