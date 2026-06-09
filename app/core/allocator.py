"""Core allocation engine: stabilisation + pool fill + fairness."""
from __future__ import annotations
import math
from collections import defaultdict
from typing import Callable

from app.core.fair_algorithm import get_strategy
from app.core.models import AllocationResult, FairnessMode, Mentor, Student
from app.utils.logger import get_logger

log = get_logger("allocator")


class Allocator:
    """Deterministic, capacity-bounded fair allocator."""

    def __init__(self, students: list[Student],
                 mentors: list[Mentor]) -> None:
        self.students     = students
        self.mentors      = mentors
        self.mentor_names = {m.name for m in mentors}

    def compute_capacity(self) -> int:
        """Return ceil(students / mentors)."""
        return math.ceil(len(self.students) / max(1, len(self.mentors)))

    def run(self, mode: FairnessMode = FairnessMode.ROUND_ROBIN,
            progress: Callable[[int, str], None] | None = None
            ) -> AllocationResult:
        """Execute allocation.

        Args:
            mode:     Fairness algorithm to use.
            progress: Optional callback ``(percent, message)``.

        Returns:
            Populated :class:`AllocationResult`.
        """
        def step(p: int, msg: str) -> None:
            log.debug("[%3d%%] %s", p, msg)
            if progress:
                progress(p, msg)

        step(10, "محاسبه ظرفیت...")
        capacity = self.compute_capacity()
        log.info("ظرفیت هر پشتیبان: %d", capacity)

        step(25, "نگاشت اولیه دانش‌آموزان...")
        initial: dict[str, list[int]] = defaultdict(list)
        for s in self.students:
            if s.initial_supporter in self.mentor_names:
                initial[s.initial_supporter].append(s.index)

        step(45, "تثبیت دانش‌آموزان...")
        stabilized: set[int] = set()
        assigned:   dict[str, list[int]] = defaultdict(list)
        for m in self.mentors:
            for idx in initial.get(m.name, [])[:capacity]:
                assigned[m.name].append(idx)
                stabilized.add(idx)
        log.info("تعداد تثبیت‌شده: %d", len(stabilized))

        pool = [s.index for s in self.students
                if s.index not in stabilized]
        log.info("اندازه pool: %d", len(pool))

        step(70, "محاسبه ظرفیت باقیمانده...")
        remaining = {
            m.name: capacity - len(assigned.get(m.name, []))
            for m in self.mentors}

        step(85, f"توزیع منصفانه ({mode.value})...")
        added = get_strategy(mode).distribute(pool, self.mentors, remaining)
        for name, idxs in added.items():
            assigned[name].extend(idxs)

        step(100, "ساخت نتیجه نهایی...")
        result = AllocationResult(
            self.students, self.mentors, capacity,
            dict(assigned), stabilized)
        for name, idxs in assigned.items():
            for idx in idxs:
                self.students[idx].final_supporter = name
        log.info("تخصیص کامل شد — مجموع: %d",
                 sum(len(v) for v in assigned.values()))
        return result
