"""Student timetable tools for AI Campus Assistant.

Supports:
- Today / tomorrow / yesterday relative queries (timezone-aware)
- Specific weekdays (Monday - Sunday)
- Full week / overview ('all', 'week')
- Safe student ID resolution and missing-student handling
"""

from datetime import datetime, timedelta
import zoneinfo
from typing import Any, Dict, List, Union
from database import get_connection
from config import get_campus_timezone

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _get_current_weekday(offset_days: int = 0) -> str:
    """Get weekday name taking campus timezone into account."""
    tz_name = get_campus_timezone()
    try:
        tz = zoneinfo.ZoneInfo(tz_name)
        now = datetime.now(tz)
    except Exception:
        now = datetime.now()
    target_date = now + timedelta(days=offset_days)
    return target_date.strftime("%A")


def resolve_day_query(day_str: str) -> str:
    """Resolve user day queries such as 'today', 'tomorrow', or weekdays."""
    cleaned = str(day_str).strip().lower()

    if cleaned in ("all", "week", "weekly", "full", "complete"):
        return "all"
    if cleaned in ("today", "todays", "today's"):
        return _get_current_weekday(0)
    if cleaned in ("tomorrow", "tomorrows", "tomorrow's"):
        return _get_current_weekday(1)
    if cleaned in ("yesterday", "yesterdays", "yesterday's"):
        return _get_current_weekday(-1)

    # Check for weekday matches
    for wd in WEEKDAYS:
        if wd.lower() == cleaned:
            return wd

    # Fallback to original string capitalized
    return day_str.strip().capitalize()


def get_student_timetable(student_id: Union[int, str], day: str = "all") -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    """Retrieve a student's timetable.

    Args:
        student_id: Numeric student ID (e.g. 101).
        day: Weekday ('Monday', 'Tuesday', ...), 'today', 'tomorrow', or 'all'.

    Returns:
        List of timetable classes or dictionary with error/message.
    """
    try:
        sid = int(student_id)
    except (ValueError, TypeError):
        return {"error": f"Invalid student ID '{student_id}'. Student ID must be an integer."}

    conn = get_connection()
    cursor = conn.cursor()

    # Check if student exists
    cursor.execute("SELECT student_id, name, department FROM students WHERE student_id = ?", (sid,))
    student = cursor.fetchone()
    if not student:
        conn.close()
        return {"error": f"Student with ID {sid} not found in database."}

    target_day = resolve_day_query(day)

    if target_day == "all":
        cursor.execute(
            """
            SELECT day, course, time, room
            FROM timetable
            WHERE student_id = ?
            ORDER BY
                CASE day
                    WHEN 'Monday' THEN 1
                    WHEN 'Tuesday' THEN 2
                    WHEN 'Wednesday' THEN 3
                    WHEN 'Thursday' THEN 4
                    WHEN 'Friday' THEN 5
                    WHEN 'Saturday' THEN 6
                    WHEN 'Sunday' THEN 7
                    ELSE 8
                END,
                time
            """,
            (sid,),
        )
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return {"message": f"No classes scheduled for student {student['name']}."}

        return [
            {
                "day": r["day"],
                "course": r["course"],
                "time": r["time"],
                "room": r["room"],
            }
            for r in rows
        ]

    # Specific day query
    cursor.execute(
        """
        SELECT day, course, time, room
        FROM timetable
        WHERE student_id = ?
          AND LOWER(day) = LOWER(?)
        ORDER BY time
        """,
        (sid, target_day),
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return {"message": f"No classes found for {target_day}."}

    return [
        {
            "day": r["day"],
            "course": r["course"],
            "time": r["time"],
            "room": r["room"],
        }
        for r in rows
    ]
