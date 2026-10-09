"""Room availability and booking management tools for AI Campus Assistant.

Features:
- Half-open interval conflict detection [start_time, end_time)
- 24-hour time normalization (handles '10:00 AM', '2 PM', '14:00', etc.)
- Strict atomic transaction conflict checks and reservations
- Authorized booking cancellation and detail queries
- Date and interval validation
"""

import re
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
import sqlite3
from database import get_connection


def normalize_time(time_str: str) -> str:
    """Normalize various time representations into 24-hour 'HH:MM' format.

    Examples:
        '10:00 AM' -> '10:00'
        '2:00 PM'  -> '14:00'
        '2 PM'     -> '14:00'
        '14:00'    -> '14:00'
        '9:30'     -> '09:30'
    """
    clean = str(time_str).strip()
    match = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$", clean, re.IGNORECASE)
    if not match:
        raise ValueError(f"Invalid time format '{time_str}'. Please use format like '10:00 AM', '2 PM', or '14:00'.")

    hours = int(match.group(1))
    minutes = int(match.group(2)) if match.group(2) else 0
    meridiem = match.group(3).lower() if match.group(3) else None

    if minutes < 0 or minutes > 59:
        raise ValueError("Minutes must be between 00 and 59.")

    if meridiem:
        if hours < 1 or hours > 12:
            raise ValueError("12-hour format hours must be between 1 and 12.")
        if meridiem == "pm" and hours != 12:
            hours += 12
        elif meridiem == "am" and hours == 12:
            hours = 0
    else:
        if hours < 0 or hours > 23:
            raise ValueError("24-hour format hours must be between 0 and 23.")

    return f"{hours:02d}:{minutes:02d}"


def normalize_date(date_str: str) -> str:
    """Normalize date string to 'YYYY-MM-DD' format. Supports 'today' and 'tomorrow'."""
    clean = str(date_str).strip().lower()
    today = date.today()

    if clean in ("today", "todays", "today's"):
        return today.isoformat()
    if clean in ("tomorrow", "tomorrows", "tomorrow's"):
        return (today + timedelta(days=1)).isoformat()

    try:
        parsed = datetime.strptime(clean, "%Y-%m-%d").date()
        return parsed.isoformat()
    except ValueError:
        pass

    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%b %d, %Y", "%B %d, %Y"):
        try:
            parsed = datetime.strptime(clean, fmt).date()
            return parsed.isoformat()
        except ValueError:
            continue

    raise ValueError(f"Invalid date format '{date_str}'. Please use 'YYYY-MM-DD' (e.g. 2026-10-15), 'today', or 'tomorrow'.")


def intervals_overlap(start_a: str, end_a: str, start_b: str, end_b: str) -> bool:
    """Check whether two half-open intervals [start_a, end_a) and [start_b, end_b) overlap."""
    return start_a < end_b and end_a > start_b


def check_room_availability(
    booking_date: str,
    start_time: str,
    end_time: str,
    min_capacity: Optional[int] = None,
) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    """Check which rooms are available for a given date and time interval.

    Uses half-open intervals [start_time, end_time).
    """
    try:
        norm_date = normalize_date(booking_date)
        norm_start = normalize_time(start_time)
        norm_end = normalize_time(end_time)
    except ValueError as e:
        return {"error": str(e)}

    if norm_start >= norm_end:
        return {"error": f"Start time ({start_time}) must be earlier than end time ({end_time})."}

    conn = get_connection()
    cursor = conn.cursor()

    # Query all active rooms
    cursor.execute("SELECT id, room_name, building, capacity FROM rooms WHERE available = 1")
    rooms = cursor.fetchall()

    if not rooms:
        conn.close()
        return {"message": "No active rooms registered on campus."}

    # Query all existing bookings for that date
    cursor.execute(
        """
        SELECT room_name, start_time, end_time
        FROM bookings
        WHERE booking_date = ?
        """,
        (norm_date,),
    )
    existing_bookings = cursor.fetchall()
    conn.close()

    available_rooms = []
    for room in rooms:
        r_name = room["room_name"]
        capacity = room["capacity"]

        if min_capacity and capacity < min_capacity:
            continue

        conflict = False
        for b in existing_bookings:
            if b["room_name"].lower() == r_name.lower():
                try:
                    b_start = normalize_time(b["start_time"])
                    b_end = normalize_time(b["end_time"])
                    if intervals_overlap(norm_start, norm_end, b_start, b_end):
                        conflict = True
                        break
                except ValueError:
                    continue

        if not conflict:
            available_rooms.append({
                "room": r_name,
                "building": room["building"],
                "capacity": capacity,
            })

    if not available_rooms:
        return {
            "message": f"No rooms are available on {norm_date} between {norm_start} and {norm_end}.",
            "available": False,
        }

    return available_rooms


def book_room(
    student_id: Union[int, str],
    room_name: str,
    booking_date: str,
    start_time: str,
    end_time: str,
    purpose: str,
) -> Dict[str, Any]:
    """Reserve a classroom or seminar hall atomically.

    Verifies availability, room existence, student record, and inserts booking.
    """
    try:
        sid = int(student_id)
    except (ValueError, TypeError):
        return {"success": False, "error": f"Invalid student ID '{student_id}'."}

    try:
        norm_date = normalize_date(booking_date)
        norm_start = normalize_time(start_time)
        norm_end = normalize_time(end_time)
    except ValueError as e:
        return {"success": False, "error": str(e)}

    if norm_start >= norm_end:
        return {"success": False, "error": f"Start time ({start_time}) must be earlier than end time ({end_time})."}

    if not purpose or not purpose.strip():
        purpose = "Academic Discussion"

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Atomic check and reservation in transaction
        cursor.execute("BEGIN IMMEDIATE")

        # Check student
        cursor.execute("SELECT student_id, name FROM students WHERE student_id = ?", (sid,))
        student = cursor.fetchone()
        if not student:
            conn.rollback()
            conn.close()
            return {"success": False, "error": f"Student with ID {sid} not found."}

        # Check room
        cursor.execute("SELECT id, room_name FROM rooms WHERE LOWER(room_name) = LOWER(?) AND available = 1", (room_name.strip(),))
        room = cursor.fetchone()
        if not room:
            conn.rollback()
            conn.close()
            return {"success": False, "error": f"Room '{room_name}' not found or is currently decommissioned."}

        canonical_room_name = room["room_name"]

        # Check conflicting bookings for this room
        cursor.execute(
            """
            SELECT id, start_time, end_time
            FROM bookings
            WHERE LOWER(room_name) = LOWER(?)
              AND booking_date = ?
            """,
            (canonical_room_name, norm_date),
        )
        existing = cursor.fetchall()
        for b in existing:
            try:
                b_start = normalize_time(b["start_time"])
                b_end = normalize_time(b["end_time"])
                if intervals_overlap(norm_start, norm_end, b_start, b_end):
                    conn.rollback()
                    conn.close()
                    return {
                        "success": False,
                        "error": f"Room '{canonical_room_name}' is already booked on {norm_date} between {b_start} and {b_end} (conflicts with requested {norm_start} to {norm_end}).",
                    }
            except ValueError:
                continue

        # Insert booking with normalized 24-hr times
        cursor.execute(
            """
            INSERT INTO bookings (student_id, room_name, booking_date, start_time, end_time, purpose)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (sid, canonical_room_name, norm_date, norm_start, norm_end, purpose.strip()),
        )
        booking_num = cursor.lastrowid
        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        return {"success": False, "error": f"Database transaction failed: {str(e)}"}

    conn.close()
    return {
        "success": True,
        "booking_id": f"HALL-{booking_num:04d}",
        "room": canonical_room_name,
        "date": norm_date,
        "start_time": norm_start,
        "end_time": norm_end,
        "purpose": purpose.strip(),
        "student_id": sid,
        "message": f"Successfully confirmed reservation for {canonical_room_name} on {norm_date} ({norm_start} - {norm_end}). Booking ID: HALL-{booking_num:04d}",
    }


def get_booking_details(booking_id: str, student_id: Optional[Union[int, str]] = None) -> Dict[str, Any]:
    """Retrieve details for a booking ID."""
    clean_id = str(booking_id).strip().upper()
    match = re.match(r"^HALL-(\d+)$", clean_id)
    if not match:
        # Also handle bare numeric IDs
        if clean_id.isdigit():
            booking_number = int(clean_id)
        else:
            return {"success": False, "error": f"Invalid booking ID '{booking_id}'. Expected format: HALL-0001."}
    else:
        booking_number = int(match.group(1))

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT b.id, b.student_id, s.name as student_name, b.room_name, b.booking_date, b.start_time, b.end_time, b.purpose
        FROM bookings b
        LEFT JOIN students s ON b.student_id = s.student_id
        WHERE b.id = ?
        """,
        (booking_number,),
    )
    result = cursor.fetchone()
    conn.close()

    if not result:
        return {"success": False, "error": f"Booking ID 'HALL-{booking_number:04d}' not found."}

    # Optional authorization check
    if student_id is not None:
        try:
            sid = int(student_id)
            if result["student_id"] != sid:
                return {
                    "success": False,
                    "error": f"Unauthorized: Booking 'HALL-{booking_number:04d}' belongs to student ID {result['student_id']}.",
                }
        except ValueError:
            pass

    return {
        "success": True,
        "booking_id": f"HALL-{result['id']:04d}",
        "student_id": result["student_id"],
        "student_name": result["student_name"] or "Student",
        "room": result["room_name"],
        "date": result["booking_date"],
        "start_time": result["start_time"],
        "end_time": result["end_time"],
        "purpose": result["purpose"],
    }


def cancel_room_booking(booking_id: str, student_id: Optional[Union[int, str]] = None) -> Dict[str, Any]:
    """Cancel a booking, with authorization enforcement."""
    clean_id = str(booking_id).strip().upper()
    match = re.match(r"^HALL-(\d+)$", clean_id)
    if not match:
        if clean_id.isdigit():
            booking_number = int(clean_id)
        else:
            return {"success": False, "error": f"Invalid booking ID '{booking_id}'. Expected format: HALL-0001."}
    else:
        booking_number = int(match.group(1))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, student_id, room_name, booking_date, start_time, end_time FROM bookings WHERE id = ?", (booking_number,))
    booking = cursor.fetchone()
    if not booking:
        conn.close()
        return {"success": False, "error": f"Booking 'HALL-{booking_number:04d}' not found."}

    # Authorization enforcement: verify requesting student owns the reservation
    if student_id is not None:
        try:
            sid = int(student_id)
            if booking["student_id"] != sid:
                conn.close()
                return {
                    "success": False,
                    "error": f"Unauthorized: You are not authorized to cancel booking 'HALL-{booking_number:04d}' (belongs to student ID {booking['student_id']}).",
                }
        except ValueError:
            pass

    cursor.execute("DELETE FROM bookings WHERE id = ?", (booking_number,))
    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": f"Booking HALL-{booking_number:04d} for {booking['room_name']} on {booking['booking_date']} was successfully cancelled.",
    }
