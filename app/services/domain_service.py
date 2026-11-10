"""Convert mapped tables to one canonical student/mentor representation."""
from __future__ import annotations

from app.core.models import Student, Mentor, WizardState
from app.services.allocation_service import _build_students, _build_mentors


def build_domain(state: WizardState) -> tuple[list[Student], list[Mentor]]:
    """Return canonical domain objects without silently dropping input rows."""
    return _build_students(state), _build_mentors(state)
