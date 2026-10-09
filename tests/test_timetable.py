"""Automated tests for student timetable queries."""

from timetable_tools import get_student_timetable, resolve_day_query


def test_timetable_specific_weekday():
    """Verify classes for a specific day."""
    res = get_student_timetable(101, "Monday")
    assert isinstance(res, list)
    assert len(res) == 2
    assert res[0]["course"] == "Computer Networks"
    assert res[1]["course"] == "Database Management Systems"


def test_timetable_all_days():
    """Verify weekly timetable retrieval."""
    res = get_student_timetable(101, "all")
    assert isinstance(res, list)
    assert len(res) >= 5


def test_timetable_no_classes_day():
    """Verify graceful message when no classes exist (e.g. Sunday)."""
    res = get_student_timetable(101, "Sunday")
    assert isinstance(res, dict)
    assert "No classes found for Sunday" in res.get("message", "")


def test_timetable_relative_day_resolution():
    """Verify today and tomorrow resolve to valid weekday names."""
    today_resolved = resolve_day_query("today")
    assert today_resolved in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    tomorrow_resolved = resolve_day_query("tomorrow")
    assert tomorrow_resolved in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def test_timetable_nonexistent_student():
    """Verify error returned when student ID does not exist."""
    res = get_student_timetable(9999, "Monday")
    assert isinstance(res, dict)
    assert "error" in res
    assert "not found" in res["error"].lower()


def test_timetable_invalid_student_id():
    """Verify error when student ID is non-numeric string."""
    res = get_student_timetable("not_an_id", "Monday")
    assert isinstance(res, dict)
    assert "error" in res
    assert "Invalid student ID" in res["error"]
