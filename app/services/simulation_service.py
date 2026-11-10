"""Simulation and reporting service."""
from __future__ import annotations

import math

from app.core.models import AllocationResult


def imbalance_report(result: AllocationResult) -> dict:
    """Mentor-level imbalance statistics."""
    loads = result.load_per_mentor()
    if not loads:
        return {
            "min": 0, "max": 0, "avg": "0.0",
            "capacity": result.capacity, "imbalance": 0,
            "loads": {},
        }
    values = list(loads.values())
    return {
        "min": min(values),
        "max": max(values),
        "avg": f"{sum(values) / len(values):.1f}",
        "capacity": result.capacity,
        "imbalance": max(values) - min(values),
        "loads": loads,
    }


def manager_report(result: AllocationResult) -> dict:
    """Manager-level fairness statistics."""
    loads = result.load_per_manager()
    targets = result.manager_targets()
    mentor_counts = result.mentors_per_manager()

    if not loads:
        return {
            "managers": [],
            "loads": {},
            "targets": {},
            "deviations": {},
            "mentor_counts": {},
            "max_deviation": 0.0,
            "min_load": 0,
            "max_load": 0,
            "avg_load": 0.0,
            "is_balanced": None,
        }

    deviations = {
        mgr: loads.get(mgr, 0) - targets.get(mgr, 0)
        for mgr in loads
    }
    values = list(loads.values())
    max_dev = (
        max(abs(d) for d in deviations.values())
        if deviations else 0.0
    )

    return {
        "managers": sorted(loads.keys()),
        "loads": loads,
        "targets": targets,
        "deviations": deviations,
        "mentor_counts": mentor_counts,
        "max_deviation": round(max_dev, 2),
        "min_load": min(values),
        "max_load": max(values),
        "avg_load": round(sum(values) / len(values), 1),
        "is_balanced": None,
    }


def detailed_report(result: AllocationResult) -> str:
    """Human-readable text report for both mentor and manager levels."""
    lines: list[str] = []

    mr = imbalance_report(result)
    lines += [
        "═══════════════════════════════════",
        "آمار سطح پشتیبان‌ها",
        "═══════════════════════════════════",
        f"حداقل بار پشتیبان:   {mr['min']}",
        f"حداکثر بار پشتیبان:  {mr['max']}",
        f"میانگین بار پشتیبان: {mr['avg']}",
        f"اختلاف حداکثر:       {mr['imbalance']}",
        f"ظرفیت هر پشتیبان:    {mr['capacity']}",
        "",
    ]

    mgr = manager_report(result)
    if mgr["managers"]:
        lines += [
            "═══════════════════════════════════",
            "آمار سطح مدیرها",
            "═══════════════════════════════════",
            f"حداقل بار مدیر:   {mgr['min_load']}",
            f"حداکثر بار مدیر:  {mgr['max_load']}",
            f"میانگین بار مدیر: {mgr['avg_load']}",
            f"حداکثر انحراف:    {mgr['max_deviation']}",
            f"وضعیت: "
            "سهم مستقل برای مدیر تعریف نشده است",
            "",
            f"{'مدیر':<20} {'پشتیبان':>8} {'هدف':>8}"
            f" {'واقعی':>8} {'انحراف':>8}",
            "─" * 56,
        ]
        for m in mgr["managers"]:
            lines.append(
                f"{m:<20} "
                f"{mgr['mentor_counts'].get(m, 0):>8} "
                f"{mgr['targets'].get(m, 0):>8.1f} "
                f"{mgr['loads'].get(m, 0):>8} "
                f"{mgr['deviations'].get(m, 0):>+8.1f}"
            )

    return "\n".join(lines)


# ── backward-compatible simulate() ──────────────────────────────

def simulate(
    students,
    mentors,
    fairness,
    capacity: int | None = None,
    stabilize_initial: bool = True,
):
    """Use the same production allocator as the main execution path."""
    from app.services.allocation_service import allocate_domain
    return allocate_domain(students, mentors, fairness, capacity, stabilize_initial)
