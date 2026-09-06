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
        ("College of Engineering, Guindy", "CEG", "https://ceg.annauniv.edu/"),
        ("Madras Institute of Technology", "MIT", "https://mitindia.edu/"),
        ("School of Architecture and Planning", "SAP", "https://www.annauniv.edu/sap/"),
        ("Alagappa College of Technology", "ACT", "https://www.annauniv.edu/act/"),
    ]
    for name, short, website_url in colleges:
        db.execute("""INSERT OR IGNORE INTO colleges
          (name,short_name,district,state,website_url) VALUES (?,?,?,?,?)""",
                   (name, short, "Chennai", "Tamil Nadu", website_url))
        db.execute(
            "UPDATE colleges SET website_url=? WHERE short_name=? AND (website_url IS NULL OR website_url='')",
            (website_url, short),
        )
    db.commit()
    db.close()


create_database()


def create_legacy_database():

    conn = get_connection()
    cursor = conn.cursor()

    # ==========================================
    # STUDENTS TABLE
    # ==========================================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        student_id INTEGER PRIMARY KEY,
        name TEXT,
        department TEXT,
        year INTEGER,
        section TEXT
    )
    """)

    # ==========================================
    # CAMPUS LOCATIONS TABLE
    # ==========================================

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

    # ==========================================
    # TIMETABLE TABLE
    # ==========================================

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
    DELETE FROM timetable
    WHERE id NOT IN (
        SELECT MIN(id)
        FROM timetable
        GROUP BY student_id, course, day, time, room
    )
    """)
    cursor.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS
    timetable_entry_unique
    ON timetable (student_id, course, day, time, room)
    """)

    # ==========================================
    # ROOMS TABLE
    # ==========================================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_name TEXT,
        building TEXT,
        capacity INTEGER,
        available INTEGER
    )
    """)

    # ==========================================
    # BOOKINGS TABLE
    # ==========================================

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

    # ==========================================
    # SAMPLE STUDENT
    # ==========================================

    cursor.execute("""
    INSERT OR IGNORE INTO students
    (student_id, name, department, year, section)
    VALUES
    (101, 'Bharathi', 'CSE', 3, 'A')
    """)

    # ==========================================
    # CAMPUS LOCATIONS
    # ==========================================

    cursor.execute("""
    INSERT OR IGNORE INTO locations
    (id, name, building, floor, room, landmark)
    VALUES
    (1, 'Computer Networks Lab',
     'CS Block', 2, 'CS-204', 'Near Main Library')
    """)

    cursor.execute("""
    INSERT OR IGNORE INTO locations
    (id, name, building, floor, room, landmark)
    VALUES
    (2, 'Database Lab',
     'IT Block', 1, 'IT-101', 'Near Seminar Hall')
    """)

    # ==========================================
    # FULL WEEK TIMETABLE
    # ==========================================

    timetable_data = [

        # Monday
        (101, "Computer Networks",
         "Monday", "10:00 AM", "CS-204"),

        (101, "Database Management Systems",
         "Monday", "2:00 PM", "IT-101"),

        # Tuesday
        (101, "Operating Systems",
         "Tuesday", "9:00 AM", "CS-201"),

        (101, "Python Programming",
         "Tuesday", "11:00 AM", "CS-205"),

        # Wednesday
        (101, "Machine Learning",
         "Wednesday", "10:00 AM", "AI-301"),

        (101, "Computer Networks Lab",
         "Wednesday", "2:00 PM", "CS-204"),

        # Thursday
        (101, "Data Structures",
         "Thursday", "9:00 AM", "CS-202"),

        (101, "Operating Systems Lab",
         "Thursday", "2:00 PM", "CS-203"),

        # Friday
        (101, "Artificial Intelligence",
         "Friday", "10:00 AM", "AI-302"),

        (101, "Database Lab",
         "Friday", "2:00 PM", "IT-101"),

        # Saturday
        (101, "Software Engineering",
         "Saturday", "9:00 AM", "CS-206"),

        (101, "Project Work",
         "Saturday", "11:00 AM", "CS-207")
    ]

    cursor.executemany("""
    INSERT OR IGNORE INTO timetable
    (student_id, course, day, time, room)
    VALUES (?, ?, ?, ?, ?)
    """, timetable_data)

    # ==========================================
    # ROOMS
    # ==========================================

    cursor.execute("""
    INSERT OR IGNORE INTO rooms
    (id, room_name, building, capacity, available)
    VALUES
    (1, 'Seminar Hall 1', 'IT Block', 60, 1)
    """)

    cursor.execute("""
    INSERT OR IGNORE INTO rooms
    (id, room_name, building, capacity, available)
    VALUES
    (2, 'Seminar Hall 2', 'IT Block', 100, 1)
    """)

    # ==========================================
    # SAVE DATABASE
    # ==========================================

    conn.commit()
    conn.close()

    print("Database initialized successfully!")


# Initialize legacy tables as well as the multi-college schema so both
# existing tool surfaces work from a fresh checkout.
create_legacy_database()

if __name__ == "__main__":
    create_database()
