"""Automated tests for room availability, interval conflict detection, and bookings."""

import pytest
from booking_tools import (
    normalize_time,
    normalize_date,
    intervals_overlap,
    check_room_availability,
    book_room,
    get_booking_details,
    cancel_room_booking,
)


def test_time_normalization():
    """Verify conversion of 12-hour and 24-hour representations."""
    assert normalize_time("10:00 AM") == "10:00"
    assert normalize_time("2:00 PM") == "14:00"
    assert normalize_time("2 PM") == "14:00"
    assert normalize_time("14:00") == "14:00"
    assert normalize_time("12:00 PM") == "12:00"
    assert normalize_time("12:00 AM") == "00:00"


def test_invalid_time_format():
    """Verify rejection of invalid time strings."""
    with pytest.raises(ValueError):
        normalize_time("25:00")
    with pytest.raises(ValueError):
        normalize_time("invalid_time")


def test_interval_overlap_logic():
    """Verify half-open interval overlap [start, end)."""
    # Overlapping intervals
    assert intervals_overlap("10:00", "12:00", "11:00", "13:00") is True
    assert intervals_overlap("11:00", "13:00", "10:00", "12:00") is True
    # Fully contained
    assert intervals_overlap("10:00", "14:00", "11:00", "12:00") is True
    # Adjacent half-open intervals: should NOT overlap!
    assert intervals_overlap("10:00", "11:00", "11:00", "12:00") is False
    assert intervals_overlap("11:00", "12:00", "10:00", "11:00") is False
    # Completely disjoint
    assert intervals_overlap("09:00", "10:00", "14:00", "15:00") is False


def test_check_availability_empty_day():
    """Verify rooms are available on an unbooked day."""
    res = check_room_availability("2026-11-01", "10:00 AM", "12:00 PM")
    assert isinstance(res, list)
    assert len(res) == 2
    room_names = [r["room"] for r in res]
    assert "Seminar Hall 1" in room_names
    assert "Seminar Hall 2" in room_names


def test_book_room_and_detect_conflict():
    """Verify booking creation and rejection of overlapping requests."""
    # Step 1: Successful booking
    booking = book_room(
        student_id=101,
        room_name="Seminar Hall 1",
        booking_date="2026-11-05",
        start_time="10:00 AM",
        end_time="12:00 PM",
        purpose="Project Demo",
    )
    assert booking["success"] is True
    b_id = booking["booking_id"]
    assert b_id.startswith("HALL-")

    # Step 2: Overlapping request for same room and date -> MUST FAIL
    overlap_attempt = book_room(
        student_id=101,
        room_name="Seminar Hall 1",
        booking_date="2026-11-05",
        start_time="11:00 AM",
        end_time="01:00 PM",
        purpose="Conflicting Talk",
    )
    assert overlap_attempt["success"] is False
    assert "already booked" in overlap_attempt["error"].lower()

    # Step 3: Adjacent request starting at 12:00 PM -> MUST SUCCEED (half-open)
    adjacent = book_room(
        student_id=101,
        room_name="Seminar Hall 1",
        booking_date="2026-11-05",
        start_time="12:00 PM",
        end_time="02:00 PM",
        purpose="Afternoon Session",
    )
    assert adjacent["success"] is True

    # Cleanup bookings
    cancel_room_booking(b_id, student_id=101)
    cancel_room_booking(adjacent["booking_id"], student_id=101)


def test_booking_invalid_time_order():
    """Verify start_time >= end_time is rejected."""
    res = book_room(
        student_id=101,
        room_name="Seminar Hall 1",
        booking_date="2026-11-06",
        start_time="03:00 PM",
        end_time="02:00 PM",
        purpose="Time Travel",
    )
    assert res["success"] is False
    assert "earlier than end time" in res["error"]


def test_booking_authorization_cancellation():
    """Verify that student A cannot cancel student B's booking."""
    booking = book_room(
        student_id=101,
        room_name="Seminar Hall 2",
        booking_date="2026-11-07",
        start_time="02:00 PM",
        end_time="04:00 PM",
        purpose="Study Group",
    )
    assert booking["success"] is True
    b_id = booking["booking_id"]

    # Student 102 attempts to cancel student 101's booking -> MUST BE BLOCKED
    unauth_cancel = cancel_room_booking(b_id, student_id=102)
    assert unauth_cancel["success"] is False
    assert "unauthorized" in unauth_cancel["error"].lower()

    # Student 101 cancels their own booking -> SUCCEEDS
    auth_cancel = cancel_room_booking(b_id, student_id=101)
    assert auth_cancel["success"] is True
    assert "successfully cancelled" in auth_cancel["message"].lower()
