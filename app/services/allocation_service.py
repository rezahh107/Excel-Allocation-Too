"""Authoritative temporary global mentor allocation path."""
from __future__ import annotations

import math

from app.core.models import AllocationResult, FairnessMode, Mentor, Role, Student, WizardState
from app.core.validation import ValidationError, validate_preconditions, ensure_result_valid


def _value(row: dict, mapping: dict[str, Role], role: Role) -> str:
    for col, mapped in mapping.items():
        if mapped == role:
            value = row.get(col, "")
            return "" if value is None else str(value).strip()
    return ""


def _build_students(state: WizardState) -> list[Student]:
    return [
        Student(
            counter=_value(row, state.map2, Role.COUNTER),
            first=_value(row, state.map2, Role.FIRST),
            last=_value(row, state.map2, Role.LAST),
            group=_value(row, state.map2, Role.GROUP),
            manager=_value(row, state.map2, Role.SMANAGER),
            initial_supporter=_value(row, state.map2, Role.INITIAL_SUPPORTER),
            grade=_value(row, state.map2, Role.GRADE),
            phone=_value(row, state.map2, Role.PHONE),
            raw=row,
        )
        for row in state.book2_rows
    ]


def _build_mentors(state: WizardState) -> list[Mentor]:
    mentors: list[Mentor] = []
    has_cap = Role.CAPACITY in state.map1.values()
    for row in state.book1_rows:
        cap: int | None = None
        if has_cap:
            cap_text = _value(row, state.map1, Role.CAPACITY)
            if cap_text:
                try:
                    cap = int(cap_text)
                except ValueError as exc:
                    raise ValidationError("ظرفیت پشتیبان باید عدد صحیح باشد.") from exc
        mentors.append(Mentor(
            name=_value(row, state.map1, Role.MENTOR_NAME),
            manager=_value(row, state.map1, Role.MANAGER_NAME),
            capacity=cap,
            raw=row,
        ))
    return mentors


def allocate_domain(
    students: list[Student],
    mentors: list[Mentor],
    mode: FairnessMode = FairnessMode.ROUND_ROBIN,
    capacity_override: int | None = None,
    stabilize_initial: bool = True,
) -> AllocationResult:
    """Give every student one internal row-index assignment with global load gap <= 1.

    A historical assignment is kept only if the mentor still has a fair quota.
    Legacy modes with incompatible semantics are rejected, not silently emulated.
    """
    if mode not in (FairnessMode.ROUND_ROBIN, FairnessMode.MENTOR_BALANCED):
        raise ValidationError("این حالت قدیمی عدالت سراسری را تضمین نمی‌کند؛ حالت نوبتی یا متعادل را انتخاب کنید.")
    validate_preconditions(students, mentors, capacity_override)
    n, k = len(students), len(mentors)
    low, extra = divmod(n, k)
    high = math.ceil(n / k)

    if capacity_override is not None:
        if type(capacity_override) is not int or capacity_override < high:
            raise ValidationError("ظرفیت دستی برای توزیع برابر کافی نیست.")

    capacities: dict[str, int] = {}
    for mentor in mentors:
        limit = mentor.capacity
        if limit is None:
            limit = high
        if type(limit) is not int or limit < 0:
            raise ValidationError("ظرفیت پشتیبان باید عدد صحیح نامنفی باشد.")
        if capacity_override is not None:
            limit = min(limit, capacity_override)
        capacities[mentor.name] = limit
        if limit < low:
            raise ValidationError("ظرفیت برخی پشتیبان‌ها با حداقل سهم برابر ناسازگار است.")

    eligible_extra = [m.name for m in mentors if capacities[m.name] >= high]
    if len(eligible_extra) < extra:
        raise ValidationError("ظرفیت کافی برای سهم‌های اضافی توزیع عادلانه وجود ندارد.")
    bonus = set(eligible_extra[:extra])
    quotas = {m.name: low + (m.name in bonus) for m in mentors}

    assigned: dict[str, list[int]] = {m.name: [] for m in mentors}
    stabilized: set[int] = set()
    names = {m.name.casefold(): m.name for m in mentors}

    if stabilize_initial:
        for i, student in enumerate(students):
            mentor_name = names.get(student.initial_supporter.strip().casefold())
            if mentor_name and len(assigned[mentor_name]) < quotas[mentor_name]:
                assigned[mentor_name].append(i)
                stabilized.add(i)

    pool = [i for i in range(n) if i not in stabilized]
    cursor = 0
    for i in pool:
        for offset in range(k):
            pos = (cursor + offset) % k
            recipient = mentors[pos].name
            if len(assigned[recipient]) < quotas[recipient]:
                assigned[recipient].append(i)
                cursor = (pos + 1) % k
                break
        else:
            raise ValidationError("ظرفیت کافی برای تخصیص همه دانش‌آموزان وجود ندارد.")

    # The result carries the effective per-mentor capacity, not an override
    # that could be mistaken for permission to violate the global quota.
    result_mentors = [
        Mentor(m.name, m.manager, capacities[m.name], m.raw)
        for m in mentors
    ]
    result = AllocationResult(
        students=list(students), mentors=result_mentors, capacity=high,
        fairness=mode, stabilized=stabilized, assigned=assigned,
    )
    ensure_result_valid(result)
    return result


def allocate(state: WizardState) -> AllocationResult:
    """Single production entry point used for preview and final acceptance."""
    return allocate_domain(
        _build_students(state), _build_mentors(state),
        state.fairness, state.capacity_override, state.stabilize_initial,
    )
