"""SQLite persistence and schema for the campus assistant.

The schema deliberately keeps college_id on every college-owned record so a
future college can be added without changing the agent.
"""
import sqlite3
from pathlib import Path

DB_NAME = str(Path(__file__).with_name("campus.db"))


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_database():
    db = get_connection()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS colleges (
      id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, short_name TEXT UNIQUE NOT NULL,
      district TEXT NOT NULL, state TEXT NOT NULL, website_url TEXT, logo_url TEXT, description TEXT,
      is_active INTEGER NOT NULL DEFAULT 1, last_scraped_at TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
      password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'student', college_id INTEGER,
      department TEXT, section TEXT, semester INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY(college_id) REFERENCES colleges(id)
    );
    CREATE TABLE IF NOT EXISTS campus_locations (
      id INTEGER PRIMARY KEY AUTOINCREMENT, college_id INTEGER NOT NULL, building_name TEXT,
      location_name TEXT NOT NULL, block TEXT, floor TEXT, department TEXT, description TEXT,
      latitude REAL, longitude REAL, map_label TEXT, source_url TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      updated_at TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(college_id) REFERENCES colleges(id)
    );
    CREATE TABLE IF NOT EXISTS college_maps (
      id INTEGER PRIMARY KEY AUTOINCREMENT, college_id INTEGER NOT NULL, map_url TEXT, map_image_url TEXT,
      latitude REAL, longitude REAL, description TEXT, source_url TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      updated_at TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(college_id) REFERENCES colleges(id)
    );
    CREATE TABLE IF NOT EXISTS map_locations (
      id INTEGER PRIMARY KEY AUTOINCREMENT, college_id INTEGER NOT NULL, building_name TEXT,
      latitude REAL, longitude REAL, description TEXT, map_label TEXT, source_url TEXT,
      FOREIGN KEY(college_id) REFERENCES colleges(id)
    );
    CREATE TABLE IF NOT EXISTS timetables (
      id INTEGER PRIMARY KEY AUTOINCREMENT, college_id INTEGER NOT NULL, department TEXT, section TEXT,
      semester INTEGER, day TEXT, start_time TEXT, end_time TEXT, subject TEXT, faculty TEXT, room TEXT,
      source_url TEXT, updated_at TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(college_id) REFERENCES colleges(id)
    );
    CREATE TABLE IF NOT EXISTS hostels (
      id INTEGER PRIMARY KEY AUTOINCREMENT, college_id INTEGER NOT NULL, hostel_name TEXT, gender TEXT,
      room_type TEXT, capacity INTEGER, occupied INTEGER, available INTEGER, facilities TEXT,
      source_url TEXT, updated_at TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(college_id) REFERENCES colleges(id)
    );
    CREATE TABLE IF NOT EXISTS announcements (
      id INTEGER PRIMARY KEY AUTOINCREMENT, college_id INTEGER NOT NULL, title TEXT, content TEXT,
      published_date TEXT, source_url TEXT, scraped_at TEXT DEFAULT CURRENT_TIMESTAMP, content_hash TEXT,
      FOREIGN KEY(college_id) REFERENCES colleges(id)
    );
    CREATE TABLE IF NOT EXISTS events (
      id INTEGER PRIMARY KEY AUTOINCREMENT, college_id INTEGER NOT NULL, title TEXT, description TEXT,
      event_type TEXT, event_date TEXT, venue TEXT, source_url TEXT, scraped_at TEXT DEFAULT CURRENT_TIMESTAMP,
      content_hash TEXT, FOREIGN KEY(college_id) REFERENCES colleges(id)
    );
    CREATE TABLE IF NOT EXISTS courses (
      id INTEGER PRIMARY KEY AUTOINCREMENT, college_id INTEGER NOT NULL, course_name TEXT, degree TEXT,
      department TEXT, duration TEXT, description TEXT, source_url TEXT, scraped_at TEXT DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY(college_id) REFERENCES colleges(id)
    );
    CREATE TABLE IF NOT EXISTS academic_calendar (
      id INTEGER PRIMARY KEY AUTOINCREMENT, college_id INTEGER NOT NULL, academic_year TEXT, semester TEXT,
      event_name TEXT, event_date TEXT, description TEXT, source_url TEXT, scraped_at TEXT DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY(college_id) REFERENCES colleges(id)
    );
    CREATE TABLE IF NOT EXISTS scraped_pages (
      id INTEGER PRIMARY KEY AUTOINCREMENT, college_id INTEGER NOT NULL, url TEXT, page_type TEXT, content TEXT,
      content_hash TEXT, scraped_at TEXT DEFAULT CURRENT_TIMESTAMP, status TEXT, error_message TEXT,
      FOREIGN KEY(college_id) REFERENCES colleges(id)
    );
    CREATE TABLE IF NOT EXISTS rag_chunks (
      id INTEGER PRIMARY KEY AUTOINCREMENT, college_id INTEGER NOT NULL, college_name TEXT, source_url TEXT,
      page_type TEXT, title TEXT, content TEXT, chunk_index INTEGER, scraped_at TEXT,
      FOREIGN KEY(college_id) REFERENCES colleges(id)
    );
    CREATE TABLE IF NOT EXISTS conversations (
      id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, college_id INTEGER NOT NULL, title TEXT,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY(user_id) REFERENCES users(id), FOREIGN KEY(college_id) REFERENCES colleges(id)
    );
    CREATE TABLE IF NOT EXISTS messages (
      id INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id INTEGER NOT NULL, role TEXT NOT NULL,
      content TEXT NOT NULL, tool_name TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY(conversation_id) REFERENCES conversations(id)
    );
    """)
    colleges = [
        ("College of Engineering, Guindy", "CEG"),
        ("Madras Institute of Technology", "MIT"),
        ("School of Architecture and Planning", "SAP"),
        ("Alagappa College of Technology", "ACT"),
    ]
    for name, short in colleges:
        db.execute("""INSERT OR IGNORE INTO colleges
          (name,short_name,district,state) VALUES (?,?,?,?)""",
                   (name, short, "Chennai", "Tamil Nadu"))
    db.commit()
    db.close()


create_database()
