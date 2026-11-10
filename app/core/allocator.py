"""Compatibility facade over the authoritative global mentor allocation service."""
from __future__ import annotations

import math
from typing import Callable

from app.core.models import AllocationResult, FairnessMode, Mentor, Student
from app.services.allocation_service import allocate_domain


class Allocator:
    def __init__(self, students: list[Student], mentors: list[Mentor]) -> None:
        self.students = students
        self.mentors = mentors

    def compute_capacity(self) -> int:
        return math.ceil(len(self.students) / max(1, len(self.mentors)))

    def run(
        self,
        mode: FairnessMode = FairnessMode.ROUND_ROBIN,
        progress: Callable[[int, str], None] | None = None,
    ) -> AllocationResult:
        if progress:
            progress(10, "بررسی شرایط تخصیص...")
        result = allocate_domain(self.students, self.mentors, mode)
        if progress:
            progress(100, "تخصیص معتبر آماده است.")
        return result
