"""Pluggable fairness strategies — Strategy pattern."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict

from app.core.models import FairnessMode, Mentor
from app.utils.logger import get_logger

log = get_logger("fair_algorithm")


class FairnessStrategy(ABC):
    """Distribute pool students across mentors with free capacity."""

    @abstractmethod
    def distribute(
        self,
        pool: list[int],
        mentors: list[Mentor],
        remaining: dict[str, int],
    ) -> dict[str, list[int]]:
        """Return mapping mentor_name -> added student indices."""


class OriginalStrategy(FairnessStrategy):
    """Legacy fill-in-order behaviour."""

    def distribute(
        self,
        pool: list[int],
        mentors: list[Mentor],
        remaining: dict[str, int],
    ) -> dict[str, list[int]]:
        log.debug("Original: توزیع %d دانش‌آموز", len(pool))
        out: dict[str, list[int]] = {m.name: [] for m in mentors}

        for idx in pool:
            target = next(
                (m.name for m in mentors if remaining.get(m.name, 0) > 0),
                None,
            )
            if target is None:
                raise RuntimeError("ظرفیت کافی برای تخصیص وجود ندارد.")
            out[target].append(idx)
            remaining[target] -= 1

        return out


class RoundRobinStrategy(FairnessStrategy):
    """Deterministic cyclic distribution — default."""

    def distribute(
        self,
        pool: list[int],
        mentors: list[Mentor],
        remaining: dict[str, int],
    ) -> dict[str, list[int]]:
        log.debug("RoundRobin: توزیع %d دانش‌آموز", len(pool))
        out: dict[str, list[int]] = {m.name: [] for m in mentors}

        order = [m.name for m in mentors]
        if not order:
            if pool:
                raise RuntimeError("هیچ پشتیبانی برای تخصیص وجود ندارد.")
            return out

        start_idx = 0
        n = len(order)

        for student_idx in pool:
            placed = False

            for offset in range(n):
                pos = (start_idx + offset) % n
                mentor_name = order[pos]
                if remaining.get(mentor_name, 0) > 0:
                    out[mentor_name].append(student_idx)
                    remaining[mentor_name] -= 1
                    start_idx = (pos + 1) % n
                    placed = True
                    break

            if not placed:
                raise RuntimeError("ظرفیت کافی برای تخصیص وجود ندارد.")

        return out


class MentorBalancedStrategy(FairnessStrategy):
    """Choose the least-loaded mentor among those with free capacity."""

    def distribute(
        self,
        pool: list[int],
        mentors: list[Mentor],
        remaining: dict[str, int],
    ) -> dict[str, list[int]]:
        log.debug("MentorBalanced: توزیع %d دانش‌آموز", len(pool))
        out: dict[str, list[int]] = {m.name: [] for m in mentors}
        order_index = {m.name: i for i, m in enumerate(mentors)}
        initial_remaining = dict(remaining)

        def mentor_added_load(name: str) -> int:
            return max(
                0,
                initial_remaining.get(name, 0) - remaining.get(name, 0),
            )

        for student_idx in pool:
            candidates = [
                m for m in mentors
                if remaining.get(m.name, 0) > 0
            ]
            if not candidates:
                raise RuntimeError("ظرفیت کافی برای تخصیص وجود ندارد.")

            best = min(
                candidates,
                key=lambda m: (
                    mentor_added_load(m.name),
                    order_index[m.name],
                ),
            )
            out[best.name].append(student_idx)
            remaining[best.name] -= 1

        return out


class ManagerBalancedStrategy(FairnessStrategy):
    """Balance managers first, then mentors, deterministically."""

    def distribute(
        self,
        pool: list[int],
        mentors: list[Mentor],
        remaining: dict[str, int],
    ) -> dict[str, list[int]]:
        log.debug("ManagerBalanced: توزیع %d دانش‌آموز", len(pool))
        out: dict[str, list[int]] = {m.name: [] for m in mentors}
        order_index = {m.name: i for i, m in enumerate(mentors)}
        initial_remaining = dict(remaining)

        manager_groups: dict[str, list[Mentor]] = defaultdict(list)
        for mentor in mentors:
            manager_groups[_manager_name(mentor)].append(mentor)

        mentor_loads: dict[str, int] = {
            m.name: max(
                0,
                initial_remaining.get(m.name, 0) - remaining.get(m.name, 0),
            )
            for m in mentors
        }

        manager_loads: dict[str, int] = {
            manager: sum(mentor_loads[m.name] for m in group)
            for manager, group in manager_groups.items()
        }

        for student_idx in pool:
            candidates = [
                m for m in mentors
                if remaining.get(m.name, 0) > 0
            ]
            if not candidates:
                raise RuntimeError("ظرفیت کافی برای تخصیص وجود ندارد.")

            best = min(
                candidates,
                key=lambda m: (
                    manager_loads.get(_manager_name(m), 0),
                    mentor_loads.get(m.name, 0),
                    order_index[m.name],
                ),
            )

            out[best.name].append(student_idx)
            remaining[best.name] -= 1

            mentor_loads[best.name] = mentor_loads.get(best.name, 0) + 1
            manager_name = _manager_name(best)
            manager_loads[manager_name] = (
                manager_loads.get(manager_name, 0) + 1
            )

        return out


def get_strategy(mode: FairnessMode) -> FairnessStrategy:
    """Factory: return concrete strategy for *mode*."""
    mapping: dict[FairnessMode, type[FairnessStrategy]] = {
        FairnessMode.ORIGINAL: OriginalStrategy,
        FairnessMode.ROUND_ROBIN: RoundRobinStrategy,
        FairnessMode.MENTOR_BALANCED: MentorBalancedStrategy,
        FairnessMode.MANAGER_BALANCED: ManagerBalancedStrategy,
    }
    strategy_cls = mapping.get(mode, RoundRobinStrategy)
    return strategy_cls()


def _manager_name(mentor: Mentor) -> str:
    value = getattr(mentor, "manager", None)
    return (value or "بدون مدیر").strip() or "بدون مدیر"
