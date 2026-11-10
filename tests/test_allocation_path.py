"""Synthetic regression tests of the real preview/final/export allocation path."""
from collections import Counter
from copy import deepcopy

import pytest
from openpyxl import load_workbook

from app.core.models import FairnessMode, Role, WizardState
from app.core.validation import (
    AllocationError, IntegrityError, IntegrityReason, ValidationError,
    validate_result,
)
from app.services.allocation_service import allocate
from app.services.domain_service import build_domain
from app.services.excel_service import export_excel, export_html_report
from app.services.simulation_service import simulate


def make_state(n=120, k=60, concentrated=False):
    assert k > 0
    mentors = [
        {"mentor": f"M{i:03}", "manager": "Manager-A" if i < k // 3 else "Manager-B"}
        for i in range(k)
    ]
    students = [
        {"student-id": f"T{i:04}", "first": f"First{i}", "last": "Synthetic",
         "previous": "M000" if concentrated else ""}
        for i in range(n)
    ]
    return WizardState(
        book1_rows=mentors, book2_rows=students,
        map1={"mentor": Role.MENTOR_NAME, "manager": Role.MANAGER_NAME},
        map2={"student-id": Role.COUNTER, "first": Role.FIRST,
              "last": Role.LAST, "previous": Role.INITIAL_SUPPORTER},
        fairness=FairnessMode.ROUND_ROBIN,
        stabilize_initial=concentrated,
    )


def check_counts(result, n, k):
    assert result.total_students == n
    assert result.total_mentors == k
    loads = result.load_per_mentor()
    assert len(loads) == k
    assert sorted(loads.values()) == sorted(
        [n // k] * (k - n % k) + [n // k + 1] * (n % k)
    )
    assert sum(map(len, result.assigned.values())) == n
    assert sorted(i for ids in result.assigned.values() for i in ids) == list(range(n))
    assert validate_result(result) == []


@pytest.mark.parametrize("n,k,expected", [
    (120, 60, {2: 60}),
    (121, 60, {2: 59, 3: 1}),
    (3, 8, {0: 5, 1: 3}),
])
def test_global_fairness(n, k, expected):
    result = allocate(make_state(n, k))
    check_counts(result, n, k)
    assert dict(Counter(result.load_per_mentor().values())) == expected


def test_managers_do_not_have_independent_quota():
    result = allocate(make_state(120, 60))
    assert result.mentors_per_manager() == {"Manager-A": 20, "Manager-B": 40}
    assert result.load_per_manager() == {"Manager-A": 40, "Manager-B": 80}
    check_counts(result, 120, 60)


def test_concentrated_history_is_bounded_by_global_quota():
    result = allocate(make_state(121, 60, concentrated=True))
    check_counts(result, 121, 60)
    assert len(result.stabilized) <= 3
    assert result.load_per_mentor()["M000"] == 3


def test_repeatability_and_input_order_invariant():
    state = make_state(121, 60, concentrated=True)
    a = allocate(state)
    b = allocate(state)
    assert a.assignment_snapshot() == b.assignment_snapshot()
    state.book1_rows.reverse()
    state.book2_rows.reverse()
    check_counts(allocate(state), 121, 60)


def test_same_core_used_by_simulation_and_main():
    state = make_state(121, 60, concentrated=True)
    preview = allocate(state)
    students, mentors = build_domain(state)
    alternate_entry = simulate(students, mentors, state.fairness, stabilize_initial=True)
    assert preview.assignment_snapshot() == alternate_entry.assignment_snapshot()


def test_duplicate_mentor_rows_are_not_silently_dropped():
    state = make_state(4, 2)
    state.book1_rows[1]["mentor"] = state.book1_rows[0]["mentor"]
    with pytest.raises(ValidationError, match="duplicate"):
        allocate(state)


@pytest.mark.parametrize("n,k", [(0, 2), (2, 0)])
def test_empty_input_is_rejected(n, k):
    state = make_state(n, max(k, 1))
    if k == 0:
        state.book1_rows = []
    with pytest.raises(ValidationError):
        allocate(state)


@pytest.mark.parametrize("mode", [FairnessMode.ORIGINAL, FairnessMode.MANAGER_BALANCED])
def test_unsafe_legacy_modes_are_explicitly_rejected(mode):
    state = make_state(120, 60)
    state.fairness = mode
    with pytest.raises(ValidationError, match="قدیمی"):
        allocate(state)


def test_manual_capacity_below_equal_quota_rejected():
    state = make_state(121, 60)
    state.capacity_override = 2
    with pytest.raises(ValidationError, match="ظرفیت"):
        allocate(state)


def test_infeasible_per_mentor_capacity_is_rejected():
    state = make_state(121, 60)
    state.map1["cap"] = Role.CAPACITY
    for row in state.book1_rows:
        row["cap"] = "2"
    with pytest.raises(ValidationError, match="ظرفیت"):
        allocate(state)


def test_zero_capacity_mentors_can_participate_when_n_is_smaller_than_k():
    state = make_state(3, 8)
    state.map1["cap"] = Role.CAPACITY
    for index, row in enumerate(state.book1_rows):
        row["cap"] = "1" if index < 3 else "0"
    check_counts(allocate(state), 3, 8)


def test_no_silent_invalid_manager_row():
    state = make_state(10, 3)
    state.book1_rows[0]["manager"] = ""
    with pytest.raises(ValidationError):
        allocate(state)


@pytest.mark.parametrize("invalid", [True, 0.5, "0", None])
def test_invalid_internal_student_references_rejected(invalid):
    result = allocate(make_state(6, 3))
    result.assigned["M000"][0] = invalid
    issues = validate_result(result)
    assert issues and "invalid_student_references" in issues[0]


def test_missing_phantom_duplicate_and_mentor_omission_fail():
    original = allocate(make_state(6, 3))
    bad = deepcopy(original)
    bad.assigned["M001"][0] = bad.assigned["M000"][0]
    assert "Duplicate" in validate_result(bad)[0]

    bad = deepcopy(original)
    bad.assigned["M001"][0] = 999
    assert "phantom_students" in validate_result(bad)[0]

    bad = deepcopy(original)
    bad.assigned["M001"].pop()
    assert "missing_students" in validate_result(bad)[0]

    bad = deepcopy(original)
    bad.assigned["GHOST"] = bad.assigned.pop("M002")
    assert "phantom_mentors" in validate_result(bad)[0]

    bad = allocate(make_state(2, 4))
    del bad.assigned["M003"]  # absent mentor must not vanish even with zero students
    assert "missing_mentors" in validate_result(bad)[0]


def test_fairness_negative_control_even_when_capacity_and_total_pass():
    result = allocate(make_state(121, 60))
    assert validate_result(result) == []
    source = "M001"  # 2 -> 1
    target = "M002"  # 2 -> 3, still <= ceil(121/60)
    idx = result.assigned[source].pop()
    result.assigned[target].append(idx)
    assert "global_mentor_fairness" in validate_result(result)[0]


def test_stale_input_and_unapproved_result_cannot_export(tmp_path):
    state = make_state(10, 3)
    result = allocate(state)
    state.result = result
    state.result_input_signature = state.input_signature()
    with pytest.raises(ValidationError):
        export_excel(result, {m.name: m.manager for m in result.mentors},
                     str(tmp_path / "not-approved.xlsx"))
    assert not (tmp_path / "not-approved.xlsx").exists()
    state.book2_rows[0]["first"] = "Changed"
    with pytest.raises(ValidationError, match="قدیمی"):
        state.assert_current_result()


def test_exact_preview_final_excel_and_html_match(tmp_path):
    state = make_state(121, 60, concentrated=True)
    result = allocate(state)
    reviewed = result.assignment_snapshot()
    state.result = result
    state.result_input_signature = state.input_signature()
    state.preview_reviewed = True
    result.mark_approved()
    assert state.assert_current_result(require_approved=True) is result
    excel_path = tmp_path / "allocation.xlsx"
    html_path = tmp_path / "report.html"
    export_excel(result, {m.name: m.manager for m in result.mentors}, str(excel_path))
    export_html_report(result, str(html_path))
    wb = load_workbook(excel_path)
    rows = list(wb.worksheets[0].values)
    assert len(rows) == 122
    assert [
        (i, rows[i + 1][6])
        for i in range(121)
    ] == [(i, result.mentor_for_student(i)) for i in range(121)]
    assert reviewed == result.assignment_snapshot()
    assert '"loads"' in html_path.read_text(encoding="utf-8")
    assert result.load_per_manager() == {
        "Manager-A": sum(result.load_per_mentor()[m.name] for m in result.mentors[:20]),
        "Manager-B": sum(result.load_per_mentor()[m.name] for m in result.mentors[20:]),
    }


def test_approval_fails_after_manual_change_even_if_still_fair():
    result = allocate(make_state(121, 60))
    result.mark_approved()
    idx = result.assigned["M000"].pop()
    result.assigned["M001"].append(idx)
    assert validate_result(result) == []  # shifted remainder is still fair
    with pytest.raises(ValidationError, match="تغییر"):
        result.assert_approved()


def test_formula_like_text_stays_inert_in_xlsx_and_html(tmp_path):
    state = make_state(3, 2)
    state.book2_rows[0]["first"] = '=HYPERLINK("https://invalid.test","X")'
    state.book2_rows[1]["first"] = '</script><script>alert("X")</script>'
    result = allocate(state)
    result.mark_approved()
    excel_path = tmp_path / "safe.xlsx"
    html_path = tmp_path / "safe.html"
    export_excel(result, {m.name: m.manager for m in result.mentors}, str(excel_path))
    export_html_report(result, str(html_path))
    cell = load_workbook(excel_path).active["B2"]
    assert cell.data_type == "s"
    assert cell.value.startswith("=HYPERLINK")
    html = html_path.read_text(encoding="utf-8")
    assert '</script><script>alert' not in html


def test_postapproval_output_data_mutation_is_rejected(tmp_path):
    result = allocate(make_state(6, 3))
    result.mark_approved()
    result.students[0].first = "Changed after approval"
    with pytest.raises(ValidationError, match="تغییر"):
        export_excel(result, {m.name: m.manager for m in result.mentors},
                     str(tmp_path / "should-not-exist.xlsx"))
    assert not (tmp_path / "should-not-exist.xlsx").exists()


def test_wrong_external_manager_mapping_cannot_change_canonical_output(tmp_path):
    result = allocate(make_state(6, 3))
    result.mark_approved()
    with pytest.raises(ValueError, match="نگاشت مدیران"):
        export_excel(result, {"M000": "Wrong Manager"}, str(tmp_path / "wrong.xlsx"))
    assert not (tmp_path / "wrong.xlsx").exists()


def test_zero_eligible_bonus_capacity_is_rejected():
    state = make_state(10, 8)
    state.map1["cap"] = Role.CAPACITY
    for i, row in enumerate(state.book1_rows):
        row["cap"] = "2" if i == 0 else "1"
    with pytest.raises(ValidationError, match="ظرفیت"):
        allocate(state)


def test_duplicate_looking_student_rows_are_not_silently_collapsed():
    state = make_state(8, 3)
    state.book2_rows[1]["student-id"] = state.book2_rows[0]["student-id"]
    state.book2_rows[1]["first"] = state.book2_rows[0]["first"]
    result = allocate(state)
    check_counts(result, 8, 3)
    assert result.students[0].counter == result.students[1].counter
    # A real-world student identity policy is not invented by this test.


@pytest.mark.parametrize("change", ["capacity", "mode", "mapping", "stabilize", "mentor"])
def test_settings_or_input_change_invalidates_previously_reviewed_result(change):
    state = make_state(12, 4)
    state.result = allocate(state)
    state.result_input_signature = state.input_signature()
    state.preview_reviewed = True
    state.result.mark_approved()

    if change == "capacity":
        state.capacity_override = 7
    elif change == "mode":
        state.fairness = FairnessMode.MENTOR_BALANCED
    elif change == "mapping":
        state.map2["last"] = Role.GRADE
    elif change == "stabilize":
        state.stabilize_initial = True
    elif change == "mentor":
        state.book1_rows[0]["manager"] = "ChangedManager"

    with pytest.raises(ValidationError, match="قدیمی"):
        state.assert_current_result(require_approved=True)
