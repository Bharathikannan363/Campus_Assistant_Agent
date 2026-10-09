"""Campus location tools for AI Campus Assistant.

Supports exact matches, common abbreviations, synonyms, landmark lookups,
multi-match resolution, and complete campus location directory queries.
"""

from typing import Any, Dict, List
from database import get_connection

SYNONYMS = {
    "networks lab": "Computer Networks Lab",
    "network lab": "Computer Networks Lab",
    "cn lab": "Computer Networks Lab",
    "db lab": "Database Lab",
    "database lab": "Database Lab",
    "dbms lab": "Database Lab",
    "chemistry lab": "Chemistry Lab",
    "chemsitry lab": "Chemistry Lab",
    "chem lab": "Chemistry Lab",
    "chemistry": "Chemistry Lab",
    "physics lab": "Physics Lab",
    "physics": "Physics Lab",
    "phy lab": "Physics Lab",
    "library": "Main Library",
    "main library": "Main Library",
    "central library": "Main Library",
    "workshop": "Central Workshop",
    "mechanical workshop": "Central Workshop",
    "canteen": "Campus Canteen",
    "cafeteria": "Campus Canteen",
    "auditorium": "Main Auditorium",
    "dean office": "Dean Office",
    "deans office": "Dean Office",
    "health centre": "Campus Health Centre",
    "health center": "Campus Health Centre",
    "clinic": "Campus Health Centre",
}

GENERIC_FACILITY_TERMS = {
    "the", "where", "is", "a", "an", "find", "want", "know", "location", "located",
    "lab", "laboratory", "hall", "room", "block", "building", "tell", "me", "about"
}


def search_campus_location(name: str) -> Dict[str, Any]:
    """Search for campus locations by name, landmark, building, or room.

    Supports:
    - Exact names and partial keywords
    - Common abbreviations (CN lab, DB lab)
    - 'all' or 'list' to show all campus locations
    - Multi-match handling with clear details
    """
    if not name or not name.strip():
        return {"error": "Please provide a location name to search."}

    query = name.strip()
    lowered = query.lower()

    conn = get_connection()
    cursor = conn.cursor()

    # Case 1: Student asks for all locations
    if lowered in ("all", "list", "show all", "locations", "all locations", "all labs"):
        cursor.execute("SELECT name, building, floor, room, landmark FROM locations ORDER BY name")
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            return {"error": "No campus locations registered in the database."}
        locations = [
            {
                "name": r["name"],
                "building": r["building"],
                "floor": r["floor"],
                "room": r["room"],
                "landmark": r["landmark"],
            }
            for r in rows
        ]
        return {
            "all_locations": locations,
            "count": len(locations),
            "message": f"Found {len(locations)} registered campus locations.",
        }

    # Case 2: Synonym mapping
    resolved_name = SYNONYMS.get(lowered, query)

    # Search in legacy locations table
    cursor.execute(
        """
        SELECT name, building, floor, room, landmark
        FROM locations
        WHERE LOWER(name) LIKE ?
           OR LOWER(building) LIKE ?
           OR LOWER(room) LIKE ?
           OR LOWER(landmark) LIKE ?
        """,
        (f"%{resolved_name.lower()}%", f"%{resolved_name.lower()}%",
         f"%{resolved_name.lower()}%", f"%{resolved_name.lower()}%"),
    )
    rows = cursor.fetchall()

    # If no match, try searching by specific discriminating words (excluding generic words like 'lab', 'room')
    if not rows and len(query.split()) > 1:
        words = [w for w in query.split() if len(w) >= 3 and w.lower() not in GENERIC_FACILITY_TERMS]
        for word in words:
            cursor.execute(
                """
                SELECT name, building, floor, room, landmark
                FROM locations
                WHERE LOWER(name) LIKE ? OR LOWER(landmark) LIKE ?
                """,
                (f"%{word.lower()}%", f"%{word.lower()}%"),
            )
            rows = cursor.fetchall()
            if rows:
                break

    conn.close()

    if not rows:
        return {"error": f"Location '{name}' not found."}

    if len(rows) == 1:
        r = rows[0]
        return {
            "name": r["name"],
            "building": r["building"],
            "floor": r["floor"],
            "room": r["room"],
            "landmark": r["landmark"],
        }

    # Multiple locations matched
    matches = [
        {
            "name": r["name"],
            "building": r["building"],
            "floor": r["floor"],
            "room": r["room"],
            "landmark": r["landmark"],
        }
        for r in rows
    ]
    summary = ", ".join(f"{m['name']} ({m['building']})" for m in matches)
    return {
        "multiple_matches": True,
        "matches": matches,
        "message": f"Found {len(matches)} matching locations: {summary}",
    }


def list_all_campus_locations() -> List[Dict[str, Any]]:
    """Retrieve all locations from database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, building, floor, room, landmark FROM locations ORDER BY name")
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "name": r["name"],
            "building": r["building"],
            "floor": r["floor"],
            "room": r["room"],
            "landmark": r["landmark"],
        }
        for r in rows
    ]
