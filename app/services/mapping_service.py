"""Fuzzy auto-detection of column roles."""
from __future__ import annotations
from difflib import SequenceMatcher

from app.core.models import Role
from app.utils.logger import get_logger

log = get_logger("mapping_service")

_HINTS: dict[Role, list[str]] = {
    Role.SUPPORTER: ["نام پشتیبان", "پشتیبان", "support", "mentor"],
    Role.MANAGER:   ["نام مدیر",    "مدیر گروه"],
    Role.COUNTER:   ["شمارنده",     "id", "کد", "شماره"],
    Role.FIRST:     ["نام",         "first", "name"],
    Role.LAST:      ["نام خانوادگی","last",  "family"],
    Role.GROUP:     ["نام گروه",    "گروه",  "group"],
    Role.SMANAGER:  ["مدیر"],
    Role.INITIAL:   ["پشتیبان",     "support", "mentor"],
}


def _score(col: str, hint: str) -> float:
    col, hint = col.lower(), hint.lower()
    if col == hint:
        return 1.0
    if hint in col or col in hint:
        return 0.9
    return SequenceMatcher(None, col, hint).ratio()


def auto_detect(columns: list[str],
                roles: set[Role]) -> dict[str, Role]:
    """Suggest a role for each column using fuzzy matching."""
    scored: list[tuple[float, str, Role]] = []
    for col in columns:
        for role in roles:
            best = max(
                (_score(col, h) for h in _HINTS.get(role, [])),
                default=0.0)
            scored.append((best, col, role))
    scored.sort(reverse=True)
    mapping: dict[str, Role] = {}
    used_roles: set[Role] = set()
    used_cols:  set[str]  = set()
    for sc, col, role in scored:
        if sc < 0.55 or col in used_cols or role in used_roles:
            continue
        mapping[col] = role
        used_cols.add(col)
        used_roles.add(role)
    for col in columns:
        mapping.setdefault(col, Role.NONE)
    log.debug("auto_detect نتیجه: %s", mapping)
    return mapping
