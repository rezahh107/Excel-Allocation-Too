"""Qt offscreen regression for Method B approval and export navigation."""
from collections import Counter

import pytest
from openpyxl import load_workbook
from PySide6.QtCore import QCoreApplication, QEvent, QTimer, Qt
from PySide6.QtWidgets import QApplication, QMessageBox, QWizard
from PySide6.QtTest import QTest

from app.services.allocation_service import allocate
from app.ui.main_window import MainWindow
from app.ui.widgets.confirm_execution_dialog import ConfirmExecutionDialog
from tests.test_allocation_path import make_state


_APP = QApplication.instance() or QApplication([])


@pytest.fixture
def window(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "qt-settings"))
    w = MainWindow()
    # Keep the WizardState instance shared with each genuine page.
    w.wizard.state.__dict__.update(make_state(121, 60).__dict__)
    w.show()
    _APP.processEvents()
    yield w
    w.close()
    w.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    _APP.processEvents()


def _unapproved_result(window):
    state = window.wizard.state
    state.result = allocate(state)
    state.result_input_signature = state.input_signature()
    return state


def _answer_dialog(accept):
    dialogs = [
        widget for widget in QApplication.topLevelWidgets()
        if isinstance(widget, ConfirmExecutionDialog) and widget.isVisible()
    ]
    assert len(dialogs) == 1, "Real confirmation modal was not shown"
    (dialogs[0].accept if accept else dialogs[0].reject)()


def test_unapproved_result_blocks_export_entry_routes(window, monkeypatch, tmp_path):
    wizard = window.wizard
    ids = wizard.pageIds()
    state = _unapproved_result(window)
    assert state.result is not None and not state.export_eligible()
    dest = tmp_path / "must-stay-absent.xlsx"
    wizard.s6.path.setText(str(dest))
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: QMessageBox.StandardButton.No)

    window._open_wizard_page(5)
    assert wizard.currentId() != ids[5]
    window._export_from_normal()
    assert wizard.currentId() != ids[5]
    window.normal_workspace._quick_export()
    assert wizard.currentId() != ids[5]
    window.normal_workspace._open_nav_item(window.normal_workspace.nav.item(5))
    assert wizard.currentId() != ids[5]

    wizard._global_export()
    wizard.setCurrentId(ids[5])
    assert wizard.currentId() != ids[5]
    QWizard.setCurrentId(wizard, ids[5])
    _APP.processEvents()
    assert wizard.currentId() != ids[5]

    wizard.s6.export()
    assert not dest.exists()
    assert not state.export_eligible()
    assert not wizard.s6.export_btn.isEnabled()


def test_real_modal_cancel_approval_export_then_undo_redo(window, tmp_path):
    wizard = window.wizard
    ids = wizard.pageIds()
    state = wizard.state
    wizard.setCurrentId(ids[3])
    assert wizard.currentId() == ids[3]
    before = state.result.assignment_snapshot()
    moved = state.result.assigned["M000"][-1]
    wizard.s4._on_move(moved, "M000", "M001")
    assert state.result.assignment_snapshot() != before
    wizard.next()
    assert wizard.currentId() == ids[4] and state.preview_reviewed
    assert not state.export_eligible() and not wizard.s5.isComplete()

    QTimer.singleShot(0, lambda: _answer_dialog(False))
    wizard.s5.run_btn.click()
    assert not state.export_eligible() and wizard.currentId() == ids[4]

    QTimer.singleShot(0, lambda: _answer_dialog(True))
    wizard.s5.run_btn.click()
    _APP.processEvents()
    assert state.export_eligible() and wizard.currentId() == ids[5]
    out = tmp_path / "approved.xlsx"
    wizard.s6.path.setText(str(out))
    wizard.s6.export_btn.click()
    assert out.is_file()
    wb = load_workbook(out)
    rows = list(wb.active.values)
    assert len(rows) == 122
    assert [(i, rows[i + 1][6]) for i in range(121)] == [
        (i, state.result.mentor_for_student(i)) for i in range(121)
    ]
    wb.close()
    assert Counter(state.result.load_per_mentor().values()) == Counter({2: 59, 3: 1})
    assert sum(state.result.load_per_manager().values()) == 121
    assert not (tmp_path / "approved_report.html").exists()

    previous_bytes = out.read_bytes()
    wizard.s4.undo_stack.undo()
    assert state.result is not None and not state.preview_reviewed
    assert not state.export_eligible()
    _APP.processEvents()
    assert wizard.currentId() != ids[5]
    wizard.s6.export()
    assert out.read_bytes() == previous_bytes
    wizard.s4.undo_stack.redo()
    assert not state.export_eligible()
    assert out.read_bytes() == previous_bytes

    # Legitimate recovery after the same invalidation must remain possible.
    wizard.setCurrentId(ids[3])
    assert wizard.currentId() == ids[3], "Re-review must remain reachable"
    wizard.next()
    assert wizard.currentId() == ids[4] and state.preview_reviewed
    QTimer.singleShot(0, lambda: _answer_dialog(True))
    wizard.s5.run_btn.click()
    _APP.processEvents()
    assert state.export_eligible() and wizard.currentId() == ids[5]
    recovered = tmp_path / "reapproved.xlsx"
    wizard.s6.path.setText(str(recovered))
    wizard.s6.export_btn.click()
    assert recovered.is_file()
    new_book = load_workbook(recovered)
    assert [r[6] for r in list(new_book.active.values)[1:]] == [
        state.result.mentor_for_student(i) for i in range(121)
    ]
    new_book.close()


def test_input_mutation_inside_modal_cannot_approve(window, tmp_path):
    wizard = window.wizard
    ids = wizard.pageIds()
    wizard.setCurrentId(ids[3])
    wizard.next()
    assert wizard.currentId() == ids[4]
    state = wizard.state

    def mutate_and_accept():
        state.book2_rows[0]["first"] = "Modified during modal"
        _answer_dialog(True)

    QTimer.singleShot(0, mutate_and_accept)
    wizard.s5.run_btn.click()
    assert not state.export_eligible()
    assert state.result.approved_assignment_snapshot is None
    assert wizard.currentId() != ids[5]
    path = tmp_path / "stale.xlsx"
    wizard.s6.path.setText(str(path))
    wizard.s6.export()
    assert not path.exists()


def test_restored_step_six_cannot_bypass_model(window, tmp_path):
    wizard = window.wizard
    wizard._apply_project_payload({
        "version": 2, "book1_path": "", "book2_path": "",
        "map1": {}, "map2": {}, "current_step_index": 5,
    })
    _APP.processEvents()
    assert wizard.state.result is None
    assert wizard.currentId() != wizard.pageIds()[5]
    out = tmp_path / "restored.xlsx"
    wizard.s6.path.setText(str(out))
    wizard.s6.export()
    assert not out.exists()


def test_real_ctrl_s_shortcut_cannot_publish_unapproved_result(window, monkeypatch, tmp_path):
    wizard = window.wizard
    state = _unapproved_result(window)
    dest = tmp_path / "ctrl-s-denied.xlsx"
    wizard.s6.path.setText(str(dest))
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: QMessageBox.StandardButton.No)

    # The MainWindow shortcut must work in Normal mode without opening export.
    window._switch_to_normal()
    assert window.stack.currentWidget() is window.normal_workspace
    window.activateWindow()
    _APP.processEvents()
    QTest.keyClick(window.normal_workspace, Qt.Key.Key_S, Qt.KeyboardModifier.ControlModifier)
    _APP.processEvents()
    assert window.stack.currentWidget() is wizard
    assert not state.export_eligible()
    assert not dest.exists()

    # The wizard's own Ctrl+S shortcut must surface the approval warning.
    window._switch_to_wizard()
    wizard.toast.hide()
    wizard.toast.clear()
    wizard.activateWindow()
    _APP.processEvents()
    QTest.keyClick(wizard, Qt.Key.Key_S, Qt.KeyboardModifier.ControlModifier)
    _APP.processEvents()
    assert "تأیید" in wizard.toast.text()
    assert not dest.exists()


def test_unapproved_step_five_allows_backward_navigation_without_approval(window):
    wizard = window.wizard
    ids = wizard.pageIds()
    wizard.setCurrentId(ids[3])
    wizard.next()
    assert wizard.currentId() == ids[4]
    assert not wizard.state.export_eligible()

    # Direct workspace/toolbar navigation back to a visited preview page
    # must work despite Step 5's forward-only approval requirement.
    wizard.setCurrentId(ids[3])
    assert wizard.currentId() == ids[3]
    assert not wizard.state.export_eligible()
    assert not wizard.state.preview_reviewed
