from database import get_connection
from web_tools import SUPPORTED_COLLEGES, search_official_website

import json



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

    cursor.execute("SELECT id FROM bookings WHERE id = ?", (booking_number,))
    if not cursor.fetchone():
        conn.close()
        return {"success": False, "error": "Booking not found."}
    cursor.execute("DELETE FROM bookings WHERE id = ?", (booking_number,))
    conn.commit(); conn.close()
    return {"success": True, "message": f"Booking HALL-{booking_number:04d} cancelled successfully."}


# The public agent surface is exactly these nine tools.  Each query is scoped
# by college_id; empty data is reported rather than guessed.
def _rows(table, college_id, where="", params=(), limit=20):
        conn = get_connection()
        rows = conn.execute(
            f"SELECT * FROM {table} WHERE college_id = ? {where} LIMIT ?",
            (college_id, *params, limit)).fetchall()
        conn.close()
        return [dict(r) for r in rows]


def search_campus_location_for_college(college_id, name):
        rows = _rows("campus_locations", college_id, "AND (location_name LIKE ? OR building_name LIKE ?)",
                     (f"%{name}%", f"%{name}%"))
        source = _college_source(college_id)
        if not rows and source:
            rows = search_official_website(source["short_name"], name)["results"]
        return {"college_id": college_id, "locations": rows,
                "sources": [{"title": r.get("title") or "Official college source", "url": r.get("url") or r.get("source_url")}
                            for r in rows if r.get("url") or r.get("source_url")]}


def get_student_timetable_for_college(college_id, department=None, section=None, semester=None, date=None, day=None):
        clauses, values = [], []
        for field, value in (("department", department), ("section", section), ("semester", semester), ("day", day)):
            if value not in (None, ""):
                clauses.append(f"AND {field} = ?"); values.append(value)
        rows = _rows("timetables", college_id, " ".join(clauses), values)
        return {"college_id": college_id, "timetable": rows,
                "message": None if rows else "I couldn't find a current timetable for this college and department."}


def check_hostel_availability(college_id, hostel_name=None, gender=None, room_type=None, academic_year=None):
        clauses, values = [], []
        for field, value in (("hostel_name", hostel_name), ("gender", gender), ("room_type", room_type)):
            if value: clauses.append(f"AND {field} LIKE ?"); values.append(f"%{value}%")
        rows = _rows("hostels", college_id, " ".join(clauses), values)
        return {"college_id": college_id, "hostels": rows,
                "message": None if rows else "Current hostel availability is not publicly available."}


def get_hostel_room_detail(college_id, hostel_name=None, room_type=None):
        return check_hostel_availability(college_id, hostel_name, room_type=room_type)


def search_college_announcements(college_id, query=None, date_from=None, date_to=None, limit=10):
        where, values = "", []
        if query: where += " AND (title LIKE ? OR content LIKE ?)"; values += [f"%{query}%", f"%{query}%"]
        rows = _rows("announcements", college_id, where, values, limit)
        source = _college_source(college_id)
        if not rows and source:
            rows = search_official_website(source["short_name"], query or "announcements", limit)["results"]
        return {"college_id": college_id, "announcements": rows,
                "sources": [{"title": r.get("title") or "Official announcement source", "url": r.get("url") or r.get("source_url")}
                            for r in rows if r.get("url") or r.get("source_url")]}


def search_college_events(college_id, query=None, date_from=None, date_to=None, event_type=None, limit=10):
        where, values = "", []
        if query: where += " AND (title LIKE ? OR description LIKE ?)"; values += [f"%{query}%", f"%{query}%"]
        if event_type: where += " AND event_type = ?"; values.append(event_type)
        return {"college_id": college_id, "events": _rows("events", college_id, where, values, limit)}


def search_course_in_college(college_id, course_name=None, degree=None, department=None, query=None):
        where, values = "", []
        for field, value in (("course_name", course_name), ("degree", degree), ("department", department)):
            if value: where += f" AND {field} LIKE ?"; values.append(f"%{value}%")
        if query: where += " AND (course_name LIKE ? OR description LIKE ?)"; values += [f"%{query}%", f"%{query}%"]
        return {"college_id": college_id, "courses": _rows("courses", college_id, where, values)}


def get_academic_calendar(college_id, academic_year=None, semester=None, event_type=None):
        where, values = "", []
        if academic_year: where += " AND academic_year = ?"; values.append(academic_year)
        if semester: where += " AND semester = ?"; values.append(semester)
        return {"college_id": college_id, "events": _rows("academic_calendar", college_id, where, values)}


def college_map(college_id, location_name=None, source_location=None, destination_location=None):
        conn = get_connection()
        maps = [dict(r) for r in conn.execute("SELECT * FROM college_maps WHERE college_id=?", (college_id,)).fetchall()]
        locations = [dict(r) for r in conn.execute("SELECT * FROM map_locations WHERE college_id=?", (college_id,)).fetchall()]
        conn.close()
        selected = next((x for x in locations if location_name and location_name.lower() in (x.get("building_name") or "").lower()), None)
        return {"college_id": college_id, "map": maps[0] if maps else None, "location": selected,
                "route": {"from": source_location, "to": destination_location, "steps": []}
                if source_location and destination_location else None,
                "message": None if maps or locations else "No official campus map has been collected."}


def get_college_official_urls(college_id):
        conn = get_connection()
        college = conn.execute(
            "SELECT name, short_name, website_url FROM colleges WHERE id=? AND is_active=1",
            (college_id,),
        ).fetchone()
        pages = conn.execute(
            "SELECT page_type, url AS source_url FROM scraped_pages "
            "WHERE college_id=? AND url IS NOT NULL AND url<>''",
            (college_id,),
        ).fetchall()
        conn.close()
        if not college:
            return {"college_id": college_id, "error": "Supported college not found.", "sources": []}
        website = college["website_url"]
        links = [{"label": "Official Website", "url": website}] if website else []
        links.append({"label": "Courses / Programs", "url": "https://cac.annauniv.edu/"})
        labels = {
            "admissions": "Admissions", "departments": "Departments",
            "courses": "Courses / Programs", "facilities": "Facilities",
            "location": "Campus / Location", "announcements": "Announcements",
            "academic": "Academic Information", "research": "Research",
            "contacts": "Contact",
        }
        seen = {website, "https://cac.annauniv.edu/"}
        for page in pages:
            if page["source_url"] in seen:
                continue
            links.append({"label": labels.get(page["page_type"], page["page_type"] or "Official Source"), "url": page["source_url"]})
            seen.add(page["source_url"])
        return {
            "college_id": college_id,
            "college": college["short_name"],
            "official_website": website,
            "links": links,
            "sources": [{"title": link["label"], "url": link["url"]} for link in links],
        }


def _college_source(college_id):
        conn = get_connection()
        row = conn.execute(
            "SELECT name, short_name, website_url FROM colleges WHERE id=? AND is_active=1",
            (college_id,),
        ).fetchone()
        conn.close()
        return dict(row) if row else None


def _search_college_content(college_id, query, page_type=None, limit=20):
        clauses = ["college_id=?", "content LIKE ?"]
        values = [college_id, f"%{query}%"]
        if page_type:
            clauses.append("page_type=?")
            values.append(page_type)
        conn = get_connection()
        rows = conn.execute(
            f"SELECT content, url AS source_url, page_type FROM scraped_pages "
            f"WHERE {' AND '.join(clauses)} ORDER BY scraped_at DESC LIMIT ?",
            (*values, limit),
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]


def search_college_information(college_id, query="college"):
        source = _college_source(college_id)
        rows = _search_college_content(college_id, query)
        if not rows and source:
            scraped = search_official_website(source["short_name"], query)
            rows = scraped["results"]
            scraped_sources = [{"title": row["title"], "url": row["url"]} for row in rows]
        else:
            scraped_sources = []
        return {"college_id": college_id, "information": rows,
                "sources": scraped_sources or [{"title": row["page_type"] or "Official college source", "url": row["source_url"]}
                            for row in rows if row.get("source_url")]
                            or ([{"title": source["short_name"] + " official website", "url": source["website_url"]}]
                                if source and source["website_url"] else [])}


def search_departments(college_id, query="department"):
        rows = _search_college_content(college_id, query, "departments")
        source = _college_source(college_id)
        if not rows and source:
            rows = search_official_website(source["short_name"], "departments")["results"]
        return {"college_id": college_id, "departments": rows,
                "sources": [{"title": row.get("title") or row.get("page_type") or "Official department source", "url": row.get("url") or row.get("source_url")}
                            for row in rows if row.get("url") or row.get("source_url")]}


def search_courses_programs(college_id, query="course"):
        courses = search_course_in_college(college_id, query=query).get("courses", [])
        source = _college_source(college_id)
        scraped = []
        if not courses and source:
            scraped = search_official_website(source["short_name"], query)["results"]
        sources = []
        if source and source["website_url"]:
            sources.append({"title": f"{source['short_name']} official website", "url": source["website_url"]})
        config = SUPPORTED_COLLEGES.get(source["short_name"]) if source else None
        if config and config.get("course_url"):
            sources.append({"title": f"{source['short_name']} official prospectus and fee structure", "url": config["course_url"]})
        sources.append({"title": "Anna University Centre for Academic Courses", "url": "https://cac.annauniv.edu/"})
        sources.extend({"title": row["title"], "url": row["url"]} for row in scraped)
        return {"college_id": college_id, "courses": courses or scraped, "sources": sources}


def search_admission_information(college_id, query="admission"):
        rows = _search_college_content(college_id, query, "admissions")
        source = _college_source(college_id)
        if not rows and source:
            rows = search_official_website(source["short_name"], "admissions")["results"]
        return {"college_id": college_id, "admissions": rows,
                "sources": [{"title": row.get("title") or row.get("page_type") or "Official admission source", "url": row.get("url") or row.get("source_url")}
                            for row in rows if row.get("url") or row.get("source_url")]}


def search_college_facilities(college_id, query="facility"):
        rows = _search_college_content(college_id, query, "facilities")
        source = _college_source(college_id)
        if not rows and source:
            rows = search_official_website(source["short_name"], "facilities")["results"]
        return {"college_id": college_id, "facilities": rows,
                "sources": [{"title": row.get("title") or row.get("page_type") or "Official facilities source", "url": row.get("url") or row.get("source_url")}
                            for row in rows if row.get("url") or row.get("source_url")]}


def search_college_contacts(college_id, query="contact"):
        rows = _search_college_content(college_id, query, "contacts")
        source = _college_source(college_id)
        if not rows and source:
            rows = search_official_website(source["short_name"], "contacts")["results"]
        return {"college_id": college_id, "contacts": rows,
                "sources": [{"title": row.get("title") or row.get("page_type") or "Official contact source", "url": row.get("url") or row.get("source_url")}
                            for row in rows if row.get("url") or row.get("source_url")]}


def search_academic_information(college_id, query="academic"):
        rows = _search_college_content(college_id, query, "academic")
        source = _college_source(college_id)
        if not rows and source:
            rows = search_official_website(source["short_name"], "academic")["results"]
        return {"college_id": college_id, "academic_information": rows,
                "sources": [{"title": row.get("title") or row.get("page_type") or "Official academic source", "url": row.get("url") or row.get("source_url")}
                            for row in rows if row.get("url") or row.get("source_url")]}


PRIMARY_TOOL_NAMES = (
        "search_college_information", "search_departments", "search_courses_programs",
        "search_admission_information", "search_college_facilities",
        "search_campus_location", "search_college_contacts",
        "search_college_announcements", "search_academic_information",
        "get_college_official_urls",
)
