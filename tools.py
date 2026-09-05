from database import get_connection


# ==========================================
# 1. SEARCH CAMPUS LOCATION
# ==========================================

def search_campus_location(name):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT name, building, floor, room, landmark
    FROM locations
    WHERE name LIKE ?
    """, (f"%{name}%",))

    result = cursor.fetchone()

    if not result:

        words = name.split()

        for word in words:

            if len(word) < 3:
                continue

            cursor.execute("""
            SELECT name, building, floor, room, landmark
            FROM locations
            WHERE name LIKE ?
            """, (f"%{word}%",))

            result = cursor.fetchone()

            if result:
                break

    conn.close()

    if result:

        return {
            "name": result[0],
            "building": result[1],
            "floor": result[2],
            "room": result[3],
            "landmark": result[4]
        }

    return {
        "error": f"Location '{name}' not found"
    }


# ==========================================
# 2. GET STUDENT TIMETABLE
# ==========================================

def get_student_timetable(student_id, day):

    conn = get_connection()
    cursor = conn.cursor()

    # ==========================================
    # FULL WEEK
    # ==========================================

    if day.lower() == "all":

        cursor.execute("""
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
            END,
            time
        """, (student_id,))

        rows = cursor.fetchall()

        conn.close()

        if not rows:
            return {
                "message": "No timetable found."
            }

        timetable = []

        for row in rows:

            timetable.append({
                "day": row[0],
                "course": row[1],
                "time": row[2],
                "room": row[3]
            })

        return timetable

    # ==========================================
    # SPECIFIC DAY
    # ==========================================

    cursor.execute("""
    SELECT course, time, room
    FROM timetable
    WHERE student_id = ?
    AND LOWER(day) = LOWER(?)
    ORDER BY time
    """, (student_id, day))

    rows = cursor.fetchall()

    conn.close()

    if not rows:

        return {
            "message": f"No classes found for {day}"
        }

    timetable = []

    for row in rows:

        timetable.append({
            "course": row[0],
            "time": row[1],
            "room": row[2]
        })

    return timetable


# ==========================================
# 3. CHECK ROOM AVAILABILITY
# ==========================================

def check_room_availability(
        booking_date,
        start_time,
        end_time):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT room_name, building, capacity
    FROM rooms
    WHERE available = 1
    """)

    rooms = cursor.fetchall()

    available_rooms = []

    for room in rooms:

        room_name = room[0]

        cursor.execute("""
        SELECT id
        FROM bookings
        WHERE room_name = ?
        AND booking_date = ?
        AND start_time < ?
        AND end_time > ?
        """, (
            room_name,
            booking_date,
            end_time,
            start_time
        ))

        conflict = cursor.fetchone()

        if not conflict:

            available_rooms.append({
                "room": room_name,
                "building": room[1],
                "capacity": room[2]
            })

    conn.close()

    if not available_rooms:

        return {
            "message": "No rooms are available for this time."
        }

    return available_rooms


# ==========================================
# 4. BOOK ROOM
# ==========================================

def book_room(
        student_id,
        room_name,
        booking_date,
        start_time,
        end_time,
        purpose):

    conn = get_connection()
    cursor = conn.cursor()

    # Check whether room exists
    cursor.execute("""
    SELECT id
    FROM rooms
    WHERE room_name = ?
    AND available = 1
    """, (room_name,))

    room = cursor.fetchone()

    if not room:

        conn.close()

        return {
            "success": False,
            "error": "Room not found or unavailable."
        }

    # Check booking conflict
    cursor.execute("""
    SELECT id
    FROM bookings
    WHERE room_name = ?
    AND booking_date = ?
    AND start_time < ?
    AND end_time > ?
    """, (
        room_name,
        booking_date,
        end_time,
        start_time
    ))

    conflict = cursor.fetchone()

    if conflict:

        conn.close()

        return {
            "success": False,
            "error": "This room is already booked for that time."
        }

    # Create booking
    cursor.execute("""
    INSERT INTO bookings
    (
        student_id,
        room_name,
        booking_date,
        start_time,
        end_time,
        purpose
    )
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        student_id,
        room_name,
        booking_date,
        start_time,
        end_time,
        purpose
    ))

    booking_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return {
        "success": True,
        "booking_id": f"HALL-{booking_id:04d}",
        "room": room_name,
        "date": booking_date,
        "start_time": start_time,
        "end_time": end_time,
        "purpose": purpose
    }


# ==========================================
# 5. GET BOOKING DETAILS
# ==========================================

def get_booking_details(booking_id):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        booking_number = int(
            booking_id.replace("HALL-", "")
        )

    except ValueError:

        conn.close()

        return {
            "success": False,
            "error": "Invalid booking ID."
        }

    cursor.execute("""
    SELECT
        id,
        student_id,
        room_name,
        booking_date,
        start_time,
        end_time,
        purpose
    FROM bookings
    WHERE id = ?
    """, (booking_number,))

    result = cursor.fetchone()

    conn.close()

    if not result:

        return {
            "success": False,
            "error": "Booking not found."
        }

    return {
        "success": True,
        "booking_id": f"HALL-{result[0]:04d}",
        "student_id": result[1],
        "room": result[2],
        "date": result[3],
        "start_time": result[4],
        "end_time": result[5],
        "purpose": result[6]
    }


# ==========================================
# 6. CANCEL BOOKING
# ==========================================

def cancel_room_booking(booking_id):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        booking_number = int(
            booking_id.replace("HALL-", "")
        )

    except ValueError:

        conn.close()

        return {
            "success": False,
            "error": "Invalid booking ID."
        }

    cursor.execute("""
    SELECT id
    FROM bookings
    WHERE id = ?
    """, (booking_number,))

    booking = cursor.fetchone()

    if not booking:

        conn.close()

        return {
            "success": False,
            "error": "Booking not found."
        }

    cursor.execute("""
    DELETE FROM bookings
    WHERE id = ?
    """, (booking_number,))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "message":
            f"Booking HALL-{booking_number:04d} "
            "cancelled successfully."
    }


# ==========================================
# TEST
# ==========================================

if __name__ == "__main__":

    print("\n===== LOCATION TEST =====")

    result = search_campus_location(
        "Computer Networks"
    )

    print(result)


    print("\n===== FULL TIMETABLE TEST =====")

    result = get_student_timetable(
        101,
        "all"
    )

    print(result)