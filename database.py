import sqlite3

DB_NAME = "campus.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def create_database():

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
    INSERT INTO timetable
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


# ==========================================
# RUN DATABASE
# ==========================================

if __name__ == "__main__":
    create_database()