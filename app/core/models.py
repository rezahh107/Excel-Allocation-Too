"""Core data models for the allocation tool."""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from enum import Enum
from typing import Optional


class Role(str, Enum):
    """Excel column roles.

    Backward-compatible names are intentionally kept because older modules
    may still import Role.SUPPORTER, Role.MANAGER, Role.INITIAL, etc.

    Canonical names:
        MENTOR_NAME
        MANAGER_NAME
        INITIAL_SUPPORTER

    Legacy aliases:
        SUPPORTER
        MANAGER
        INITIAL
    """

    NONE = "بدون نقش"
    COUNTER = "شمارنده"

    FIRST = "نام"
    LAST = "نام خانوادگی"

    INITIAL_SUPPORTER = "پشتیبان اولیه"
    INITIAL = "پشتیبان اولیه"  # legacy alias

    MENTOR_NAME = "نام پشتیبان"
    SUPPORTER = "نام پشتیبان"  # legacy alias

    MANAGER_NAME = "نام مدیر"
    MANAGER = "نام مدیر"  # legacy alias

    CAPACITY = "ظرفیت"
    GRADE = "پایه"
    PHONE = "تلفن"


    # ── backward-compatible aliases (auto-generated) ──────────
    GROUP = "نام گروه"  # alias
    SMANAGER = "مدیر ارشد"  # alias: senior/head manager


class FairnessMode(str, Enum):
    """Allocation fairness strategy."""
    ORIGINAL = "حالت اصلی / Legacy"
    ROUND_ROBIN = "نوبتی / Round Robin"
    MENTOR_BALANCED = "متعادل بین پشتیبان‌ها"
    MANAGER_BALANCED = "متعادل بین مدیرها و پشتیبان‌ها"



# ── Column role sets ──────────────────────────────────────────────
# Roles that are optional (not required) for Book1 (mentors file)
OPTIONAL_BOOK1: frozenset[Role] = frozenset({
    Role.NONE,
    Role.CAPACITY,
    Role.PHONE,
    Role.GRADE,
})

# Roles that are optional (not required) for Book2 (students file)
OPTIONAL_BOOK2: frozenset[Role] = frozenset({
    Role.NONE,
    Role.PHONE,
    Role.GRADE,
    Role.CAPACITY,
    Role.MANAGER_NAME,
    Role.INITIAL_SUPPORTER,
    Role.COUNTER,
    Role.GROUP,
    Role.SMANAGER,
})

# Roles required in Book1 (mentors)
REQUIRED_BOOK1: frozenset[Role] = frozenset({
    Role.MENTOR_NAME,
    Role.MANAGER_NAME,
})

# Roles required in Book2 (students)
REQUIRED_BOOK2: frozenset[Role] = frozenset({
    Role.FIRST,
    Role.LAST,
})

@dataclass
class Student:
    counter: str = ""
    first: str = ""
    last: str = ""
    group: str = ""
    manager: str = ""
    initial_supporter: str = ""
    grade: str = ""
    phone: str = ""
    raw: dict = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        name = f"{self.first} {self.last}".strip()
        return name or self.counter or "بدون نام"


@dataclass
class Mentor:
    name: str = ""
    manager: str = ""
    capacity: int | None = None
    raw: dict = field(default_factory=dict)


@dataclass
class AllocationResult:
    students: list[Student] = field(default_factory=list)
    mentors: list[Mentor] = field(default_factory=list)
    capacity: int = 0
    fairness: FairnessMode = FairnessMode.ROUND_ROBIN
    stabilized: set[int] = field(default_factory=set)
    assigned: dict[str, list[int]] = field(default_factory=dict)
    num_moved: int = 0
    rebalance_moves: int = 0
    # A reviewed result is the only possible source of a final export.
    approved_assignment_snapshot: tuple | None = field(default=None, repr=False)

    def assignment_snapshot(self) -> tuple:
        return tuple(
            (name, tuple(indices))
            for name, indices in sorted(self.assigned.items())
        )

    def approval_snapshot(self) -> tuple:
        """Freeze exactly the fields consumed by exports, including provenance."""
        student_rows = tuple(
            (s.counter, s.first, s.last, s.group, s.manager,
             s.initial_supporter, s.grade, s.phone)
            for s in self.students
        )
        mentor_rows = tuple(
            (m.name, m.manager, m.capacity) for m in self.mentors
        )
        return (
            self.assignment_snapshot(), student_rows, mentor_rows,
            self.capacity, self.fairness, tuple(sorted(self.stabilized)),
            self.num_moved,
        )

    def mark_approved(self) -> None:
        from app.core.validation import ensure_result_valid
        ensure_result_valid(self)
        self.approved_assignment_snapshot = self.approval_snapshot()

    def assert_approved(self) -> None:
        from app.core.validation import ValidationError, ensure_result_valid
        ensure_result_valid(self)
        if (self.approved_assignment_snapshot is None
                or self.approval_snapshot() != self.approved_assignment_snapshot):
            raise ValidationError("نتیجه تأیید نشده یا پس از تأیید تغییر کرده است.")

    def mentor_for_student(self, index: int) -> str:
        for name, indices in self.assigned.items():
            if index in indices:
                return name
        raise ValueError(f"دانش‌آموز داخلی {index} فاقد تخصیص است.")

    @property
    def total_students(self) -> int:
        return len(self.students)

    @property
    def total_mentors(self) -> int:
        return len(self.mentors)

    def load_per_mentor(self) -> dict[str, int]:
        return {
            m.name: len(self.assigned.get(m.name, []))
            for m in self.mentors
        }

    def load_per_manager(self) -> dict[str, int]:
        totals: dict[str, int] = {}
        for mentor in self.mentors:
            mgr = mentor.manager or "بدون مدیر"
            totals[mgr] = totals.get(mgr, 0) + len(
                self.assigned.get(mentor.name, [])
            )
        return totals

    def mentors_per_manager(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for mentor in self.mentors:
            mgr = mentor.manager or "بدون مدیر"
            counts[mgr] = counts.get(mgr, 0) + 1
        return counts

    def manager_targets(self) -> dict[str, float]:
        total_mentors = self.total_mentors
        if total_mentors == 0:
            return {}
        per_manager = self.mentors_per_manager()
        return {
            mgr: round(self.total_students * cnt / total_mentors, 2)
            for mgr, cnt in per_manager.items()
        }


@dataclass
class WizardState:
    book1_path: str = ""
    book2_path: str = ""
    book1_rows: list[dict] = field(default_factory=list)
    book2_rows: list[dict] = field(default_factory=list)
    book1_headers: list[str] = field(default_factory=list)
    book2_headers: list[str] = field(default_factory=list)
    saved_map1: dict[str, str] = field(default_factory=dict)
    saved_map2: dict[str, str] = field(default_factory=dict)
    map1: dict[str, Role] = field(default_factory=dict)
    map2: dict[str, Role] = field(default_factory=dict)
    map_errors: list[str] = field(default_factory=list)
    fairness: FairnessMode = FairnessMode.ROUND_ROBIN
    capacity_override: Optional[int] = None
    stabilize_initial: bool = True
    result: Optional[AllocationResult] = None
    result_input_signature: str | None = None
    preview_reviewed: bool = False

    def input_signature(self) -> str:
        """Fingerprint imported data, mappings and settings (not real IDs)."""
        payload = {
            "book1": self.book1_rows, "book2": self.book2_rows,
            "map1": {k: v.value for k, v in self.map1.items()},
            "map2": {k: v.value for k, v in self.map2.items()},
            "mode": self.fairness.value,
            "capacity": self.capacity_override,
            "stabilize": self.stabilize_initial,
        }
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def invalidate_result(self) -> None:
        self.result = None
        self.result_input_signature = None
        self.preview_reviewed = False

    def assert_current_result(self, require_approved: bool = False) -> AllocationResult:
        from app.core.validation import ValidationError, ensure_result_valid
        if (self.result is None or self.result_input_signature is None
                or self.result_input_signature != self.input_signature()):
            raise ValidationError("پیش‌نمایش قدیمی است؛ تخصیص را دوباره بررسی کنید.")
        ensure_result_valid(self.result)
        if require_approved:
            self.result.assert_approved()
        return self.result
