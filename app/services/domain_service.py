"""Convert raw rows + mappings into domain objects."""
from __future__ import annotations

from app.core.models import Mentor, Role, Student, WizardState
from app.utils.logger import get_logger

log = get_logger("domain_service")


def build_domain(state: WizardState) -> tuple[list[Student], list[Mentor]]:
    """Return ``(students, mentors)`` from the current WizardState."""
    inv1 = {role: col for col, role in state.map1.items()}
    inv2 = {role: col for col, role in state.map2.items()}

    mentors: list[Mentor] = []
    seen: set[str] = set()
    sup_col = inv1.get(Role.SUPPORTER)
    mgr_col = inv1.get(Role.MANAGER)
    for row in state.book1_rows:
        name = row.get(sup_col, "") if sup_col else ""
        if name and name not in seen:
            seen.add(name)
            mentors.append(
                Mentor(name, row.get(mgr_col, "") if mgr_col else ""))

    students: list[Student] = []
    for i, row in enumerate(state.book2_rows):
        students.append(Student(
            index=i,
            counter =row.get(inv2.get(Role.COUNTER,  ""), ""),
            first   =row.get(inv2.get(Role.FIRST,    ""), ""),
            last    =row.get(inv2.get(Role.LAST,     ""), ""),
            group   =row.get(inv2.get(Role.GROUP,    ""), ""),
            manager =row.get(inv2.get(Role.SMANAGER, ""), ""),
            initial_supporter=row.get(inv2.get(Role.INITIAL, ""), ""),
        ))
    log.info("domain ساخته شد: %d دانش‌آموز، %d پشتیبان",
             len(students), len(mentors))
    return students, mentors
