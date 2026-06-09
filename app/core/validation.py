"""Validation utilities for mapping and allocation results."""
from __future__ import annotations
from app.core.models import AllocationResult, Role
from app.utils.logger import get_logger

log = get_logger("validation")


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
