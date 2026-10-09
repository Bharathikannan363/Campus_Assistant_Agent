"""Pytest configuration and test database fixtures."""

import os
import sqlite3
import tempfile
import pytest
from pathlib import Path


@pytest.fixture(scope="session", autouse=True)
def test_db_environment():
    """Create a temporary SQLite database for testing and isolate from production campus.db."""
    temp_dir = tempfile.mkdtemp()
    test_db_path = os.path.join(temp_dir, "test_campus.db")
    os.environ["DATABASE_PATH"] = test_db_path

    # Initialize schema
    conn = sqlite3.connect(test_db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    # Create tables
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        student_id INTEGER PRIMARY KEY,
        name TEXT,
        department TEXT,
        year INTEGER,
        section TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        building TEXT,
        floor INTEGER,
        room TEXT,
        landmark TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS timetable (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        course TEXT,
        day TEXT,
        time TEXT,
        room TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_name TEXT,
        building TEXT,
        capacity INTEGER,
        available INTEGER
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        room_name TEXT,
        booking_date TEXT,
        start_time TEXT,
        end_time TEXT,
        purpose TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS colleges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        short_name TEXT UNIQUE NOT NULL,
        district TEXT NOT NULL,
        state TEXT NOT NULL,
        website_url TEXT,
        logo_url TEXT,
        description TEXT,
        is_active INTEGER NOT NULL DEFAULT 1
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rag_chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        college_id INTEGER,
        college_name TEXT,
        source_url TEXT,
        page_type TEXT,
        title TEXT,
        content TEXT,
        chunk_index INTEGER,
        scraped_at TEXT
    )
    """)

    # Seed test student
    cursor.execute(
        "INSERT OR REPLACE INTO students VALUES (101, 'Bharathi', 'CSE', 3, 'A')"
    )
    cursor.execute(
        "INSERT OR REPLACE INTO students VALUES (102, 'Ananya', 'ECE', 2, 'B')"
    )

    # Seed test locations
    cursor.execute(
        "INSERT OR REPLACE INTO locations VALUES (1, 'Computer Networks Lab', 'CS Block', 2, 'CS-204', 'Near Main Library')"
    )
    cursor.execute(
        "INSERT OR REPLACE INTO locations VALUES (2, 'Database Lab', 'IT Block', 1, 'IT-101', 'Near Seminar Hall')"
    )
    cursor.execute(
        "INSERT OR REPLACE INTO locations VALUES (3, 'Chemistry Lab', 'Science Block', 1, 'CH-101', 'Near Physics Lab')"
    )
    cursor.execute(
        "INSERT OR REPLACE INTO locations VALUES (4, 'Physics Lab', 'Science Block', 1, 'PH-102', 'Near Chemistry Lab')"
    )
    cursor.execute(
        "INSERT OR REPLACE INTO locations VALUES (5, 'Main Library', 'Central Library Building', 0, 'LIB-01', 'Opposite CS Block')"
    )

    # Seed test rooms
    cursor.execute("INSERT OR REPLACE INTO rooms VALUES (1, 'Seminar Hall 1', 'IT Block', 60, 1)")
    cursor.execute("INSERT OR REPLACE INTO rooms VALUES (2, 'Seminar Hall 2', 'IT Block', 100, 1)")

    # Seed test timetable
    timetable_rows = [
        (101, "Computer Networks", "Monday", "10:00 AM", "CS-204"),
        (101, "Database Management Systems", "Monday", "2:00 PM", "IT-101"),
        (101, "Operating Systems", "Tuesday", "9:00 AM", "CS-201"),
        (101, "Artificial Intelligence", "Friday", "10:00 AM", "AI-302"),
        (101, "Database Lab", "Friday", "2:00 PM", "IT-101"),
    ]
    cursor.executemany(
        "INSERT INTO timetable (student_id, course, day, time, room) VALUES (?, ?, ?, ?, ?)",
        timetable_rows,
    )

    conn.commit()
    conn.close()

    yield test_db_path

    # Teardown
    if os.path.exists(test_db_path):
        try:
            os.remove(test_db_path)
        except Exception:
            pass
