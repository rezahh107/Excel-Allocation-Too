"""Pluggable fairness strategies — Strategy pattern."""
from __future__ import annotations

import math
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass

from app.core.models import FairnessMode, Mentor
from app.utils.logger import get_logger

log = get_logger("fair_algorithm")


@dataclass
class StrategyResult:
    """Result of a distribution strategy."""
    assignments: dict[str, list[int]]
    rebalance_moves: int = 0


class FairnessStrategy(ABC):
    """Distribute pool students across mentors with free capacity.

    Note on Absolute Load Awareness:
        The 'remaining' dict passed to distribute() must already reflect
        stabilized students. That is: capacity - remaining = total assigned
        (stabilized + newly allocated). If the caller does not pre-adjust
        'remaining' for stabilized assignments, only new pool students will
        be counted in the load calculation.
    """

    @abstractmethod
    def distribute(
        self,
        pool: list[int],
        mentors: list[Mentor],
        remaining: dict[str, int],
    ) -> StrategyResult:
        """Return StrategyResult with mentor->student mapping and rebalance moves."""


class OriginalStrategy(FairnessStrategy):
    """Legacy fill-in-order behaviour."""

    def distribute(
        self,
        pool: list[int],
        mentors: list[Mentor],
        remaining: dict[str, int],
    ) -> StrategyResult:
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

        return StrategyResult(assignments=out, rebalance_moves=0)


class RoundRobinStrategy(FairnessStrategy):
    """Deterministic cyclic distribution — default."""

    def distribute(
        self,
        pool: list[int],
        mentors: list[Mentor],
        remaining: dict[str, int],
    ) -> StrategyResult:
        log.debug("RoundRobin: توزیع %d دانش‌آموز", len(pool))
        out: dict[str, list[int]] = {m.name: [] for m in mentors}

        order = [m.name for m in mentors]
        if not order:
            if pool:
                raise RuntimeError("هیچ پشتیبانی برای تخصیص وجود ندارد.")
            return StrategyResult(assignments=out, rebalance_moves=0)

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

        return StrategyResult(assignments=out, rebalance_moves=0)


class MentorBalancedStrategy(FairnessStrategy):
    """Choose the least-loaded mentor using Absolute Load (stabilized + new)."""

    def distribute(
        self,
        pool: list[int],
        mentors: list[Mentor],
        remaining: dict[str, int],
    ) -> StrategyResult:
        log.debug("MentorBalanced: توزیع %d دانش‌آموز", len(pool))
        out: dict[str, list[int]] = {m.name: [] for m in mentors}
        order_index = {m.name: i for i, m in enumerate(mentors)}
        cap_map = {m.name: max(0, getattr(m, 'capacity', 0) or 0) for m in mentors}

        def _abs_load(m_name: str) -> int:
            return max(0, cap_map.get(m_name, 0) - remaining.get(m_name, 0))

        for student_idx in pool:
            candidates = [m for m in mentors if remaining.get(m.name, 0) > 0]
            if not candidates:
                raise RuntimeError("ظرفیت کافی برای تخصیص وجود ندارد.")

            best = min(
                candidates,
                key=lambda m: (_abs_load(m.name), order_index[m.name]),
            )
            out[best.name].append(student_idx)
            remaining[best.name] -= 1

        return StrategyResult(assignments=out, rebalance_moves=0)


class ManagerBalancedStrategy(FairnessStrategy):
    """Balance managers first with Absolute Load, followed by a safe Rebalance pass."""

    def distribute(
        self,
        pool: list[int],
        mentors: list[Mentor],
        remaining: dict[str, int],
    ) -> StrategyResult:
        log.debug("ManagerBalanced: توزیع %d دانش‌آموز", len(pool))
        out: dict[str, list[int]] = {m.name: [] for m in mentors}
        order_index = {m.name: i for i, m in enumerate(mentors)}
        cap_map = {m.name: max(0, getattr(m, 'capacity', 0) or 0) for m in mentors}

        manager_groups: dict[str, list[Mentor]] = defaultdict(list)
        for mentor in mentors:
            manager_groups[_manager_name(mentor)].append(mentor)

        def _abs_load(m_name: str) -> int:
            """Absolute assigned load (stabilized + new). See class docstring."""
            return max(0, cap_map.get(m_name, 0) - remaining.get(m_name, 0))

        def _mgr_abs_load(mgr: str) -> int:
            return sum(_abs_load(m.name) for m in manager_groups[mgr])

        # ── Phase 1: Greedy Allocation ──
        for student_idx in pool:
            candidates = [m for m in mentors if remaining.get(m.name, 0) > 0]
            if not candidates:
                raise RuntimeError("ظرفیت کافی برای تخصیص وجود ندارد.")

            best = min(
                candidates,
                key=lambda m: (
                    _mgr_abs_load(_manager_name(m)),
                    _abs_load(m.name),
                    order_index[m.name],
                ),
            )
            out[best.name].append(student_idx)
            remaining[best.name] -= 1

        # ── Phase 2: Rebalance Pass (Safe & Efficient) ──
        total_mentors = len(mentors)
        if total_mentors == 0:
            return StrategyResult(assignments=out, rebalance_moves=0)

        total_load = sum(_mgr_abs_load(mgr) for mgr in manager_groups)
        targets = {
            mgr: total_load * (len(group) / total_mentors)
            for mgr, group in manager_groups.items()
        }

        max_shifts = len(pool) * 2
        shifts_done = 0

        for _ in range(50):
            improved = False

            # Compute deviations once per pass
            deviations = {
                mgr: _mgr_abs_load(mgr) - targets.get(mgr, 0)
                for mgr in manager_groups
            }

            underloaded = [
                mgr for mgr, dev in deviations.items() if dev < -0.5
            ]
            overloaded = [
                mgr for mgr, dev in deviations.items() if dev > 0.5
            ]

            if not overloaded or not underloaded:
                break

            overloaded.sort(key=lambda m: deviations[m], reverse=True)

            for over_mgr in overloaded:
                # Re-check threshold at the start of each manager
                if _mgr_abs_load(over_mgr) <= math.ceil(targets.get(over_mgr, 0)):
                    continue

                for over_m in list(manager_groups[over_mgr]):
                    # Re-check inside the mentor loop to prevent over-correction
                    if _mgr_abs_load(over_mgr) <= math.ceil(targets.get(over_mgr, 0)):
                        break
                    if not out[over_m.name]:
                        continue

                    # Find an underloaded manager that still has capacity
                    for under_mgr in underloaded:
                        receivers = [
                            m for m in manager_groups[under_mgr]
                            if remaining.get(m.name, 0) > 0
                        ]
                        if receivers:
                            best_rx = min(receivers, key=lambda m: _abs_load(m.name))
                            s_idx = out[over_m.name].pop()
                            out[best_rx.name].append(s_idx)
                            remaining[over_m.name] += 1
                            remaining[best_rx.name] -= 1
                            shifts_done += 1
                            improved = True

                            log.debug(
                                "Rebalance: شیفت دانش‌آموز %d از %s (مدیر=%s) → %s (مدیر=%s)",
                                s_idx, over_m.name, over_mgr, best_rx.name, under_mgr
                            )

                            if shifts_done >= max_shifts:
                                improved = False
                                break
                            break  # break out of under_mgr loop after first successful shift
                    if not improved or shifts_done >= max_shifts:
                        break

                if shifts_done >= max_shifts or not improved:
                    break

            if not improved:
                break

        if shifts_done > 0:
            log.info("ManagerBalanced Rebalance: %d شیفت در سکوت انجام شد.", shifts_done)

        return StrategyResult(assignments=out, rebalance_moves=shifts_done)


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