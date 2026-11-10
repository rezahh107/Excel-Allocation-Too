"""Real XLSX import -> canonical rows -> allocation -> approved Excel export."""
from openpyxl import Workbook, load_workbook

from app.core.models import Role, WizardState
from app.services.allocation_service import allocate
from app.services.excel_service import export_excel, load_table


def _write_workbook(path, headers, rows):
    wb = Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    wb.save(path)
    wb.close()


def test_real_excel_input_path_and_approved_output(tmp_path):
    mentors_path = tmp_path / "mentors.xlsx"
    students_path = tmp_path / "students.xlsx"
    export_path = tmp_path / "result.xlsx"
    _write_workbook(
        mentors_path, ["پشتیبان", "مدیر"],
        [(f"M{i:02}", "Mgr-A" if i == 0 else "Mgr-B") for i in range(4)],
    )
    _write_workbook(
        students_path, ["شناسه", "نام", "نام خانوادگی", "پشتیبان اولیه"],
        [(f"T{i:04}", f"Sample{i}", "Synthetic", "") for i in range(9)],
    )

    h1, mentors = load_table(str(mentors_path))
    h2, students = load_table(str(students_path))
    assert h1 == ["پشتیبان", "مدیر"]
    assert h2 == ["شناسه", "نام", "نام خانوادگی", "پشتیبان اولیه"]
    assert len(mentors) == 4 and len(students) == 9

    state = WizardState(
        book1_rows=mentors, book2_rows=students,
        map1={"پشتیبان": Role.MENTOR_NAME, "مدیر": Role.MANAGER_NAME},
        map2={"شناسه": Role.COUNTER, "نام": Role.FIRST,
              "نام خانوادگی": Role.LAST, "پشتیبان اولیه": Role.INITIAL_SUPPORTER},
    )
    result = allocate(state)
    state.result = result
    state.result_input_signature = state.input_signature()
    result.mark_approved()
    state.assert_current_result(require_approved=True)
    export_excel(
        result, {m.name: m.manager for m in result.mentors}, str(export_path),
    )

    out = load_workbook(export_path, data_only=True)
    values = list(out.worksheets[0].values)
    assert len(values) == 10
    assert [v[0] for v in values[1:]] == [f"T{i:04}" for i in range(9)]
    assert [v[6] for v in values[1:]] == [
        result.mentor_for_student(i) for i in range(9)
    ]
    assert [v[7] for v in values[1:]] == [
        "Mgr-A" if v[6] == "M00" else "Mgr-B" for v in values[1:]
    ]
    assert sorted(result.load_per_mentor().values()) == [2, 2, 2, 3]
    out.close()
