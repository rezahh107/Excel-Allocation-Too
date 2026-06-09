"""Validation utilities for mapping and allocation results."""
from __future__ import annotations

from enum import Enum
from typing import Any

from app.core.models import AllocationResult, Role
from app.utils.logger import get_logger

log = get_logger("validation")


# =============================================================================
# Legacy mapping/result validation APIs
# =============================================================================

def validate_mapping(mapping: dict[str, Role],
                     required: set[Role]) -> list[str]:
    """Return human-readable mapping errors (empty list = OK)."""
    errors: list[str] = []
    roles = [r for r in mapping.values() if r != Role.NONE]
    for req in required:
        if req not in roles:
            errors.append(f"نقش الزامی تعیین نشده است: {req.value}")
    seen: dict[Role, int] = {}
    for r in roles:
        seen[r] = seen.get(r, 0) + 1
    for r, c in seen.items():
        if c > 1:
            errors.append(
                f"نقش «{r.value}» به {c} ستون اختصاص یافته است.")
    if errors:
        log.debug("خطاهای نگاشت: %s", errors)
    return errors


def validate_result(result: AllocationResult) -> list[str]:
    """Verify allocation invariants; return list of violations."""
    issues: list[str] = []
    total = sum(len(v) for v in result.assigned.values())
    if total != result.total_students:
        issues.append("تعداد تخصیص‌ها با تعداد دانش‌آموزان برابر نیست.")
    for m in result.mentors:
        if len(result.assigned.get(m.name, [])) > result.capacity:
            issues.append(
                f"پشتیبان {m.name} از ظرفیت تجاوز کرده است.")
    for name, idxs in result.assigned.items():
        for idx in idxs:
            if idx in result.stabilized:
                stu = result.students[idx]
                if stu.initial_supporter != name:
                    issues.append(
                        f"دانش‌آموز تثبیت‌شده {stu.counter} "
                        f"جابه‌جا شده است.")
    if issues:
        log.warning("مشکلات اعتبارسنجی: %s", issues)
    return issues


# =============================================================================
# Allocation validation contract
# =============================================================================
#
# Policy:
# - Fail Fast
# - Typed exception hierarchy
# - No mutation of inputs
#
# Postcondition priority:
# 1. Phantom Mentor
# 2. Capacity Violation
# 3. Duplicate Assignment
# 4. Phantom Students
# 5. Missing Students
#
# Note:
# The domain rule for capacity=0 is intentionally NOT finalized here.
# Existing tests keep that rule skipped until UI/import/engine behavior is audited.
# =============================================================================


class IntegrityReason(str, Enum):
    PHANTOM_MENTORS = "phantom_mentors"
    PHANTOM_STUDENTS = "phantom_students"
    MISSING_STUDENTS = "missing_students"


class AllocationError(Exception):
    """Base exception for allocation validation errors."""


class ValidationError(AllocationError):
    """Raised when allocation input/preconditions are invalid."""


class DuplicateAssignmentError(AllocationError):
    """Raised when a student is assigned more than once."""

    def __init__(self, duplicates: list[int]):
        self.duplicates = duplicates
        super().__init__(f"Duplicate student assignments: {duplicates}")


class CapacityViolationError(AllocationError):
    """Raised when a mentor receives more students than allowed."""

    def __init__(self, mentor: str, assigned: int, capacity: int):
        self.mentor = mentor
        self.assigned = assigned
        self.capacity = capacity
        super().__init__(
            f"Capacity violation for mentor {mentor!r}: "
            f"assigned={assigned}, capacity={capacity}"
        )


class IntegrityError(AllocationError):
    """Raised when allocation output violates structural integrity."""

    def __init__(self, reason: IntegrityReason, items: list[Any]):
        self.reason = reason
        self.items = items
        super().__init__(f"Integrity error: {reason.value}: {items}")


def _normalize_required_string(value: Any, field_name: str) -> str:
    """Validate and normalize a required string field without mutating input."""
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string")

    normalized = value.strip()
    if not normalized:
        raise ValidationError(f"{field_name} cannot be empty")

    return normalized


def validate_preconditions(students, mentors, capacity: int | None = None) -> None:
    """Validate allocation inputs before running the allocation strategy.

    Contract:
    - students must not be empty
    - mentors must not be empty
    - mentor.name must be non-empty string after strip
    - mentor.manager must be non-empty string after strip
    - mentor names are compared after strip for duplicate detection
    - capacity=0 is intentionally not decided here yet
    - this function must not mutate inputs
    """
    if not students:
        raise ValidationError("students cannot be empty")

    if not mentors:
        raise ValidationError("mentors cannot be empty")

    normalized_names: list[str] = []

    for mentor in mentors:
        name = _normalize_required_string(
            getattr(mentor, "name", None),
            "mentor.name",
        )
        _normalize_required_string(
            getattr(mentor, "manager", None),
            "mentor.manager",
        )
        normalized_names.append(name)

    seen: set[str] = set()
    duplicates: list[str] = []

    for name in normalized_names:
        if name in seen and name not in duplicates:
            duplicates.append(name)
        seen.add(name)

    if duplicates:
        raise ValidationError(f"duplicate mentor names: {duplicates}")

    # Only validate capacity type for now.
    # Do NOT enforce capacity <= 0 yet; domain rule is still open.
    if capacity is not None and not isinstance(capacity, int):
        raise ValidationError("capacity must be an int or None")


def validate_postconditions(students, mentors, assigned: dict[str, list[int]]) -> None:
    """Validate allocation output after strategy execution.

    Fail-fast priority:
    1. Phantom Mentor
    2. Capacity Violation
    3. Duplicate Assignment
    4. Phantom Students
    5. Missing Students

    This function must not mutate students, mentors, or assigned.
    """
    mentor_capacity: dict[str, int] = {}

    for mentor in mentors:
        name = getattr(mentor, "name", "")
        if isinstance(name, str):
            name = name.strip()
        mentor_capacity[name] = getattr(mentor, "capacity", 0)

    mentor_names = set(mentor_capacity.keys())

    # 1. Phantom Mentor
    phantom_mentors = [name for name in assigned.keys() if name not in mentor_names]
    if phantom_mentors:
        raise IntegrityError(
            IntegrityReason.PHANTOM_MENTORS,
            phantom_mentors,
        )

    # 2. Capacity Violation
    for mentor_name, student_indices in assigned.items():
        capacity = mentor_capacity[mentor_name]
        if len(student_indices) > capacity:
            raise CapacityViolationError(
                mentor=mentor_name,
                assigned=len(student_indices),
                capacity=capacity,
            )

    # Flatten assigned indices without mutating inputs.
    all_assigned: list[int] = []
    for student_indices in assigned.values():
        all_assigned.extend(student_indices)

    # 3. Duplicate Assignment
    seen_students: set[int] = set()
    duplicates: list[int] = []

    for index in all_assigned:
        if index in seen_students and index not in duplicates:
            duplicates.append(index)
        seen_students.add(index)

    if duplicates:
        raise DuplicateAssignmentError(duplicates)

    expected_students = set(range(len(students)))
    actual_students = set(all_assigned)

    # 4. Phantom Students
    phantom_students = sorted(actual_students - expected_students)
    if phantom_students:
        raise IntegrityError(
            IntegrityReason.PHANTOM_STUDENTS,
            phantom_students,
        )

    # 5. Missing Students
    missing_students = sorted(expected_students - actual_students)
    if missing_students:
        raise IntegrityError(
            IntegrityReason.MISSING_STUDENTS,
            missing_students,
        )