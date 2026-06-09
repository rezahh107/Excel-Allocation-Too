"""Test Suite for Allocation Validation Layer (Red Phase)."""
import copy
import pytest
from dataclasses import dataclass, field


# --- Test Doubles ---
@dataclass
class FakeMentor:
    name: str = ""
    manager: str = ""
    capacity: int = 0
    raw: dict = field(default_factory=dict)


@dataclass
class FakeStudent:
    counter: str = ""
    first: str = ""
    last: str = ""
    initial_supporter: str = ""
    raw: dict = field(default_factory=dict)


from app.core.validation import (
    validate_preconditions,
    validate_postconditions,
    AllocationError,
    ValidationError,
    DuplicateAssignmentError,
    CapacityViolationError,
    IntegrityError,
    IntegrityReason,
)


def make_students(n):
    return [FakeStudent(counter=str(i)) for i in range(n)]


def make_mentors(specs):
    """specs = [(name, capacity, manager), ...]"""
    return [FakeMentor(name=n, capacity=c, manager=m) for (n, c, m) in specs]


# ============ PRECONDITIONS ============

class TestPreconditions:
    def test_empty_students_raises(self):
        with pytest.raises(ValidationError):
            validate_preconditions([], make_mentors([("A", 5, "M1")]), capacity=5)

    def test_empty_mentors_raises(self):
        with pytest.raises(ValidationError):
            validate_preconditions(make_students(3), [], capacity=5)

    def test_duplicate_mentor_names_raises(self):
        mentors = make_mentors([("A", 5, "M1"), ("A", 3, "M2")])
        with pytest.raises(ValidationError):
            validate_preconditions(make_students(3), mentors, capacity=5)

    def test_duplicate_mentor_names_after_strip(self):
        """نام‌هایی که فقط با فاصله فرق دارند، باید duplicate محسوب شوند."""
        mentors = [
            FakeMentor(name="Ali", manager="M1", capacity=5),
            FakeMentor(name=" Ali ", manager="M2", capacity=5),
        ]

        with pytest.raises(ValidationError):
            validate_preconditions(make_students(2), mentors, capacity=5)

    def test_empty_mentor_name_raises(self):
        """نام خالی یا فقط فاصله نباید معتبر باشد."""
        mentors = make_mentors([("", 5, "M1"), ("   ", 3, "M2")])
        with pytest.raises(ValidationError):
            validate_preconditions(make_students(3), mentors, capacity=5)

    def test_valid_input_passes(self):
        mentors = make_mentors([("A", 5, "M1"), ("B", 5, "M1")])
        validate_preconditions(make_students(3), mentors, capacity=5)


# ============ MANAGER VALIDATION ============

class TestManagerValidation:
    def test_empty_manager_raises(self):
        mentors = make_mentors([("A", 5, "")])
        with pytest.raises(ValidationError):
            validate_preconditions(make_students(3), mentors, capacity=5)

    def test_manager_name_whitespace_invalid(self):
        mentors = [
            FakeMentor(name="A", manager="   ", capacity=5),
        ]

        with pytest.raises(ValidationError):
            validate_preconditions(make_students(2), mentors, capacity=5)

    def test_non_string_manager_raises(self):
        mentors = [FakeMentor(name="A", manager=123, capacity=5)]  # type: ignore[arg-type]
        with pytest.raises(ValidationError):
            validate_preconditions(make_students(3), mentors, capacity=5)


# ============ CAPACITY=0 (تصمیم دامنه‌ای باز) ============

@pytest.mark.skip(reason="Domain rule for capacity=0 not finalized yet")
class TestZeroCapacityRule:
    def test_zero_capacity_behavior(self):
        """رفتار capacity=0 تا تثبیت قانون دامنه نامشخص است."""
        pass


# ============ POSTCONDITIONS ============

class TestPostconditions:
    def test_valid_allocation_passes(self):
        mentors = make_mentors([("A", 2, "M1"), ("B", 2, "M1")])
        validate_postconditions(make_students(4), mentors, {"A": [0, 1], "B": [2, 3]})

    def test_duplicate_assignment_payload(self):
        mentors = make_mentors([("A", 5, "M1"), ("B", 5, "M1")])
        assigned = {"A": [0, 1], "B": [1, 2]}

        with pytest.raises(DuplicateAssignmentError) as exc:
            validate_postconditions(make_students(3), mentors, assigned)

        assert exc.value.duplicates == [1]

    def test_capacity_violation_payload(self):
        mentors = make_mentors([("A", 2, "M1")])

        with pytest.raises(CapacityViolationError) as exc:
            validate_postconditions(make_students(3), mentors, {"A": [0, 1, 2]})

        assert exc.value.mentor == "A"
        assert exc.value.assigned == 3
        assert exc.value.capacity == 2

    def test_phantom_student_payload(self):
        mentors = make_mentors([("A", 5, "M1")])

        with pytest.raises(IntegrityError) as exc:
            validate_postconditions(make_students(2), mentors, {"A": [0, 1, 99]})

        assert exc.value.reason == IntegrityReason.PHANTOM_STUDENTS
        assert exc.value.items == [99]

    def test_missing_student_payload(self):
        mentors = make_mentors([("A", 5, "M1")])

        with pytest.raises(IntegrityError) as exc:
            validate_postconditions(make_students(3), mentors, {"A": [0, 1]})

        assert exc.value.reason == IntegrityReason.MISSING_STUDENTS
        assert exc.value.items == [2]

    def test_phantom_mentor_payload(self):
        mentors = make_mentors([("A", 5, "M1")])

        with pytest.raises(IntegrityError) as exc:
            validate_postconditions(make_students(2), mentors, {"A": [0], "GHOST": [1]})

        assert exc.value.reason == IntegrityReason.PHANTOM_MENTORS
        assert exc.value.items == ["GHOST"]


# ============ VALIDATION PRIORITY ============

class TestValidationPriority:
    def test_phantom_mentor_has_priority_over_other_errors(self):
        students = make_students(2)
        mentors = make_mentors([("A", 1, "M1")])

        assigned = {
            "A": [0, 1],        # capacity violation
            "GHOST": [1, 99],   # phantom mentor + duplicate + phantom student
        }

        with pytest.raises(IntegrityError) as exc:
            validate_postconditions(students, mentors, assigned)

        assert exc.value.reason == IntegrityReason.PHANTOM_MENTORS
        assert exc.value.items == ["GHOST"]

    def test_capacity_has_priority_over_duplicate_assignment(self):
        students = make_students(3)
        mentors = make_mentors([("A", 1, "M1"), ("B", 5, "M1")])

        assigned = {
            "A": [0, 1],  # capacity violation
            "B": [1, 2],  # duplicate student 1
        }

        with pytest.raises(CapacityViolationError) as exc:
            validate_postconditions(students, mentors, assigned)

        assert exc.value.mentor == "A"

    def test_duplicate_has_priority_over_phantom_student(self):
        students = make_students(3)
        mentors = make_mentors([("A", 5, "M1"), ("B", 5, "M1")])

        assigned = {
            "A": [0, 1],
            "B": [1, 99],  # duplicate 1 + phantom 99
        }

        with pytest.raises(DuplicateAssignmentError) as exc:
            validate_postconditions(students, mentors, assigned)

        assert exc.value.duplicates == [1]

    def test_phantom_student_has_priority_over_missing_student(self):
        students = make_students(3)
        mentors = make_mentors([("A", 5, "M1")])

        assigned = {
            "A": [0, 99],  # phantom 99 + missing 1,2
        }

        with pytest.raises(IntegrityError) as exc:
            validate_postconditions(students, mentors, assigned)

        assert exc.value.reason == IntegrityReason.PHANTOM_STUDENTS
        assert exc.value.items == [99]


# ============ MUTATION SAFETY ============

class TestMutationSafety:
    def test_postconditions_do_not_mutate_inputs(self):
        students = make_students(4)
        mentors = make_mentors([("A", 2, "M1"), ("B", 2, "M1")])
        assigned = {"A": [0, 1], "B": [2, 3]}

        students_before = copy.deepcopy(students)
        mentors_before = copy.deepcopy(mentors)
        assigned_before = copy.deepcopy(assigned)

        validate_postconditions(students, mentors, assigned)

        assert students == students_before
        assert mentors == mentors_before
        assert assigned == assigned_before