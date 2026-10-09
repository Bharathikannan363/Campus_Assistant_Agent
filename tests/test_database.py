"""Automated tests for database connection and basic query execution."""

from database import get_connection, get_db_path


def test_database_connection():
    """Verify that database connection opens with foreign keys enabled."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys")
    fk = cursor.fetchone()[0]
    conn.close()
    assert fk == 1


def test_student_lookup():
    """Verify querying an existing student."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, department FROM students WHERE student_id = 101")
    row = cursor.fetchone()
    conn.close()
    assert row is not None
    assert row["name"] == "Bharathi"
    assert row["department"] == "CSE"


def test_missing_student_lookup():
    """Verify querying a non-existent student returns None."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students WHERE student_id = 9999")
    row = cursor.fetchone()
    conn.close()
    assert row is None


def test_locations_query():
    """Verify locations table query."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM locations")
    count = cursor.fetchone()[0]
    conn.close()
    assert count >= 2
