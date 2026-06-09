"""Allocation service with hierarchical manager/mentor fairness."""
from __future__ import annotations

import logging
import math
from collections import defaultdict
from typing import Callable

from app.core.models import (
    AllocationResult,
    FairnessMode,
    Mentor,
    Student,
    WizardState,
)

log = logging.getLogger(__name__)


def _build_students(state: WizardState) -> list[Student]:
    from app.core.models import Role
    students: list[Student] = []
    for row in state.book2_rows:
        def _get(role: Role, _row: dict = row) -> str:
            for col, r in state.map2.items():
                if r == role:
                    return str(_row.get(col, "")).strip()
            return ""
        students.append(
            Student(
                counter=_get(Role.COUNTER),
                first=_get(Role.FIRST),
                last=_get(Role.LAST),
                initial_supporter=_get(Role.INITIAL_SUPPORTER),
                grade=_get(Role.GRADE),
                phone=_get(Role.PHONE),
                raw=row,
            )
        )
    return students


def _build_mentors(state: WizardState, capacity: int) -> list[Mentor]:
    from app.core.models import Role
    mentors: list[Mentor] = []
    for row in state.book1_rows:
        def _get(role: Role, _row: dict = row) -> str:
            for col, r in state.map1.items():
                if r == role:
                    return str(_row.get(col, "")).strip()
            return ""
        mentors.append(
            Mentor(
                name=_get(Role.MENTOR_NAME),
                manager=_get(Role.MANAGER_NAME),
                capacity=capacity,
                raw=row,
            )
        )
    return mentors


def _initial_supporter_index(name: str, mentors: list[Mentor]) -> int | None:
    name_lower = name.lower().strip()
    for i, m in enumerate(mentors):
        if m.name.lower().strip() == name_lower:
            return i
    return None


def _compute_stabilised(
    students: list[Student],
    mentors: list[Mentor],
    stabilize_initial: bool,
) -> set[int]:
    if not stabilize_initial:
        return set()
    valid_names = {m.name.lower().strip() for m in mentors}
    return {
        i for i, s in enumerate(students)
        if s.initial_supporter.lower().strip() in valid_names
    }


# ── ORIGINAL ─────────────────────────────────────────────────────

def _allocate_original(
    students, mentors, capacity, stabilised
) -> tuple[dict[str, list[int]], int]:
    assigned: dict[str, list[int]] = {m.name: [] for m in mentors}
    num_moved = 0
    for idx in stabilised:
        s = students[idx]
        m_idx = _initial_supporter_index(s.initial_supporter, mentors)
        if m_idx is not None:
            assigned[mentors[m_idx].name].append(idx)
    remaining = [i for i in range(len(students)) if i not in stabilised]
    for idx in remaining:
        for m in mentors:
            if len(assigned[m.name]) < capacity:
                assigned[m.name].append(idx)
                num_moved += 1
                break
    return assigned, num_moved


# ── ROUND ROBIN ───────────────────────────────────────────────────

def _allocate_round_robin(
    students, mentors, capacity, stabilised
) -> tuple[dict[str, list[int]], int]:
    assigned: dict[str, list[int]] = {m.name: [] for m in mentors}
    num_moved = 0
    for idx in stabilised:
        s = students[idx]
        m_idx = _initial_supporter_index(s.initial_supporter, mentors)
        if m_idx is not None:
            assigned[mentors[m_idx].name].append(idx)
    remaining = [i for i in range(len(students)) if i not in stabilised]
    rr_idx = 0
    for idx in remaining:
        attempts = 0
        while attempts < len(mentors):
            m = mentors[rr_idx % len(mentors)]
            rr_idx += 1
            attempts += 1
            if len(assigned[m.name]) < capacity:
                assigned[m.name].append(idx)
                num_moved += 1
                break
    return assigned, num_moved


# ── MENTOR BALANCED ───────────────────────────────────────────────

def _allocate_mentor_balanced(
    students, mentors, capacity, stabilised
) -> tuple[dict[str, list[int]], int]:
    assigned: dict[str, list[int]] = {m.name: [] for m in mentors}
    num_moved = 0
    for idx in stabilised:
        s = students[idx]
        m_idx = _initial_supporter_index(s.initial_supporter, mentors)
        if m_idx is not None:
            assigned[mentors[m_idx].name].append(idx)
    remaining = [i for i in range(len(students)) if i not in stabilised]
    for idx in remaining:
        best = min(
            (m for m in mentors if len(assigned[m.name]) < capacity),
            key=lambda m: len(assigned[m.name]),
            default=None,
        )
        if best:
            assigned[best.name].append(idx)
            num_moved += 1
        else:
            log.warning("No capacity for student %d", idx)
    return assigned, num_moved


# ── MANAGER BALANCED ──────────────────────────────────────────────

def _manager_groups(mentors: list[Mentor]) -> dict[str, list[Mentor]]:
    groups: dict[str, list[Mentor]] = defaultdict(list)
    for m in mentors:
        groups[m.manager or "بدون مدیر"].append(m)
    return dict(groups)


def _compute_manager_targets(
    manager_groups: dict[str, list[Mentor]],
    total_students: int,
) -> dict[str, float]:
    total_mentors = sum(len(v) for v in manager_groups.values())
    if total_mentors == 0:
        return {}
    return {
        mgr: total_students * len(mentors) / total_mentors
        for mgr, mentors in manager_groups.items()
    }


def _best_manager(
    manager_groups: dict[str, list[Mentor]],
    manager_targets: dict[str, float],
    assigned: dict[str, list[int]],
    capacity: int,
) -> str | None:
    def _load(mgr: str) -> int:
        return sum(len(assigned[m.name]) for m in manager_groups[mgr])

    def _has_capacity(mgr: str) -> bool:
        return any(
            len(assigned[m.name]) < capacity
            for m in manager_groups[mgr]
        )

    candidates = [mgr for mgr in manager_groups if _has_capacity(mgr)]
    if not candidates:
        return None

    return min(
        candidates,
        key=lambda mgr: _load(mgr) - manager_targets.get(mgr, 0),
    )


def _best_mentor_in_manager(
    manager_name: str,
    manager_groups: dict[str, list[Mentor]],
    assigned: dict[str, list[int]],
    capacity: int,
    preferred_mentor: str | None = None,
) -> Mentor | None:
    candidates = [
        m for m in manager_groups[manager_name]
        if len(assigned[m.name]) < capacity
    ]
    if not candidates:
        return None
    if preferred_mentor:
        preferred_lower = preferred_mentor.lower().strip()
        for m in candidates:
            if m.name.lower().strip() == preferred_lower:
                return m
    return min(candidates, key=lambda m: len(assigned[m.name]))


def _rebalance_managers(
    manager_groups: dict[str, list[Mentor]],
    manager_targets: dict[str, float],
    assigned: dict[str, list[int]],
    students: list[Student],
    stabilised: set[int],
    capacity: int,
    max_passes: int = 3,
) -> int:
    moves = 0
    for _pass in range(max_passes):
        improved = False

        def _load(mgr: str) -> int:
            return sum(len(assigned[m.name]) for m in manager_groups[mgr])

        sorted_managers = sorted(
            manager_groups.keys(),
            key=lambda mgr: _load(mgr) - manager_targets.get(mgr, 0),
        )
        half = len(sorted_managers) // 2 + 1
        underloaded = sorted_managers[:half]
        overloaded = sorted_managers[half:]

        for over_mgr in overloaded:
            if _load(over_mgr) <= math.ceil(
                manager_targets.get(over_mgr, 0)
            ):
                continue
            for under_mgr in underloaded:
                if over_mgr == under_mgr:
                    continue
                if _load(under_mgr) >= math.floor(
                    manager_targets.get(under_mgr, 0)
                ):
                    continue
                for mentor in manager_groups[over_mgr]:
                    for s_idx in list(assigned[mentor.name]):
                        if s_idx in stabilised:
                            continue
                        dest = _best_mentor_in_manager(
                            under_mgr, manager_groups, assigned, capacity
                        )
                        if dest is None:
                            continue
                        assigned[mentor.name].remove(s_idx)
                        assigned[dest.name].append(s_idx)
                        moves += 1
                        improved = True
                        log.debug(
                            "Rebalance: student %d  %s -> %s",
                            s_idx, mentor.name, dest.name,
                        )
                        break
                    if improved:
                        break
                if improved:
                    break
        if not improved:
            break
    return moves


def _allocate_manager_balanced(
    students, mentors, capacity, stabilised
) -> tuple[dict[str, list[int]], int]:
    assigned: dict[str, list[int]] = {m.name: [] for m in mentors}
    num_moved = 0

    groups = _manager_groups(mentors)
    targets = _compute_manager_targets(groups, len(students))
    log.info("Manager targets: %s", targets)

    for idx in stabilised:
        s = students[idx]
        m_idx = _initial_supporter_index(s.initial_supporter, mentors)
        if m_idx is not None:
            assigned[mentors[m_idx].name].append(idx)

    remaining = [i for i in range(len(students)) if i not in stabilised]
    for idx in remaining:
        student = students[idx]
        preferred_manager: str | None = None
        if student.initial_supporter:
            m_idx = _initial_supporter_index(
                student.initial_supporter, mentors
            )
            if m_idx is not None:
                preferred_manager = mentors[m_idx].manager or "بدون مدیر"

        best_mgr = _best_manager(groups, targets, assigned, capacity)
        if best_mgr is None:
            log.warning("No manager capacity for student %d", idx)
            continue

        preferred_in_mgr = (
            student.initial_supporter
            if preferred_manager == best_mgr
            else None
        )
        dest = _best_mentor_in_manager(
            best_mgr, groups, assigned, capacity, preferred_in_mgr
        )
        if dest is None:
            log.warning(
                "No mentor capacity in %s for student %d", best_mgr, idx
            )
            continue

        assigned[dest.name].append(idx)
        num_moved += 1

    rb = _rebalance_managers(
        groups, targets, assigned, students, stabilised, capacity
    )
    log.info("Manager rebalance moved %d students", rb)

    return assigned, num_moved


# ── dispatcher ────────────────────────────────────────────────────

_STRATEGY: dict[FairnessMode, Callable] = {
    FairnessMode.ORIGINAL: _allocate_original,
    FairnessMode.ROUND_ROBIN: _allocate_round_robin,
    FairnessMode.MENTOR_BALANCED: _allocate_mentor_balanced,
    FairnessMode.MANAGER_BALANCED: _allocate_manager_balanced,
}


def allocate(state: WizardState) -> AllocationResult:
    """Run the allocation algorithm based on state.fairness mode."""
    students = _build_students(state)
    capacity = state.capacity_override or math.ceil(
        len(students) / max(len(state.book1_rows), 1)
    )
    mentors = _build_mentors(state, capacity)

    if not students:
        raise ValueError("داده‌ای برای دانش‌آموزان یافت نشد.")
    if not mentors:
        raise ValueError("داده‌ای برای پشتیبان‌ها یافت نشد.")

    stabilised = _compute_stabilised(
        students, mentors, state.stabilize_initial
    )
    strategy = _STRATEGY.get(state.fairness, _allocate_round_robin)

    log.info(
        "Allocating %d students → %d mentors using [%s]",
        len(students), len(mentors), state.fairness.value,
    )

    assigned, num_moved = strategy(students, mentors, capacity, stabilised)

    result = AllocationResult(
        students=students,
        mentors=mentors,
        capacity=capacity,
        fairness=state.fairness,
        stabilized=stabilised,
        assigned=assigned,
        num_moved=num_moved,
    )
    log.info(
        "Done. Moved=%d  Stabilised=%d", num_moved, len(stabilised)
    )
    return result
