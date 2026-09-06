import os
import json
import re
from datetime import datetime

from pathlib import Path

from memory import add_message, get_memory

from dotenv import load_dotenv
from openai import AuthenticationError, OpenAI
from database import get_connection

from tools import (
    search_campus_location,
    get_student_timetable,
    check_room_availability,
    book_room,
    get_booking_details,
    cancel_room_booking
)

from tools import (
    PRIMARY_TOOL_NAMES, search_campus_location_for_college,
    get_student_timetable_for_college, check_hostel_availability,
    get_hostel_room_detail, search_college_announcements, search_college_events,
    search_course_in_college, get_academic_calendar, college_map,
    get_college_official_urls, search_college_information, search_departments,
    search_courses_programs, search_admission_information, search_college_facilities,
    search_college_contacts, search_academic_information, _college_source
)



# ==========================================
# LOAD API KEY
# ==========================================

ENV_FILE = Path(__file__).with_name(".env")


def _api_key():
    load_dotenv(dotenv_path=ENV_FILE, override=False)
    return os.getenv("OPENROUTER_API_KEY", "").strip()


def _configured_api_key():
    key = _api_key()
    if not key:
        return None
    if not key.startswith("sk-or-"):
        raise RuntimeError(
            "OPENROUTER_API_KEY is invalid. Set it to a newly generated "
            "OpenRouter API key in the local .env file."
        )
    return key

# ==========================================
# OPENROUTER
# ==========================================


api_key = _api_key()
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key
) if api_key else None



# ==========================================
# TOOLS
# ==========================================

tools = [

    # --------------------------------------
    # SEARCH CAMPUS LOCATION
    # --------------------------------------

    {
        "type": "function",
        "function": {
            "name": "search_campus_location",
            "description": """
Find a campus location.

Use this when the student asks:
- Where is the Computer Networks lab?
- Where is Database Lab?
- Where is a classroom?
- Where is a lab?
""",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the campus location"
                    }
                },
                "required": ["name"]
            }
        }
    },


    # --------------------------------------
    # GET STUDENT TIMETABLE
    # --------------------------------------

    {
        "type": "function",
        "function": {
            "name": "get_student_timetable",
            "description": """
Get the student's timetable.

The current student ID is 101.

If the student asks:
- show timetable
- show the timetable
- show my timetable
- full timetable
- complete timetable
- all days
- all the day
- weekly timetable

use day = "all".

If the student asks for a specific day,
use that day.

If the student says "today timetable",
use today's day.
""",
            "parameters": {
                "type": "object",
                "properties": {
                    "student_id": {
                        "type": "integer",
                        "description": "Student ID. Use 101."
                    },
                    "day": {
                        "type": "string",
                        "description": """
Day name such as Monday, Tuesday,
Wednesday, Thursday, Friday, Saturday,
Sunday, or all.
"""
                    }
                },
                "required": [
                    "student_id",
                    "day"
                ]
            }
        }
    },


    # --------------------------------------
    # CHECK ROOM AVAILABILITY
    # --------------------------------------

    {
        "type": "function",
        "function": {
            "name": "check_room_availability",
            "description": """
Check which seminar halls or classrooms
are available for a particular date and time.

Use this BEFORE booking a room.
""",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_date": {
                        "type": "string",
                        "description": "Booking date"
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Starting time"
                    },
                    "end_time": {
                        "type": "string",
                        "description": "Ending time"
                    }
                },
                "required": [
                    "booking_date",
                    "start_time",
                    "end_time"
                ]
            }
        }
    },


    # --------------------------------------
    # BOOK ROOM
    # --------------------------------------

    {
        "type": "function",
        "function": {
            "name": "book_room",
            "description": """
Book a seminar hall or classroom.

ONLY use this after the student has
explicitly confirmed the booking.

First check room availability.
""",
            "parameters": {
                "type": "object",
                "properties": {
                    "student_id": {
                        "type": "integer",
                        "description": "Student ID. Use 101."
                    },
                    "room_name": {
                        "type": "string",
                        "description": "Room name"
                    },
                    "booking_date": {
                        "type": "string",
                        "description": "Booking date"
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Starting time"
                    },
                    "end_time": {
                        "type": "string",
                        "description": "Ending time"
                    },
                    "purpose": {
                        "type": "string",
                        "description": "Purpose of booking"
                    }
                },
                "required": [
                    "student_id",
                    "room_name",
                    "booking_date",
                    "start_time",
                    "end_time",
                    "purpose"
                ]
            }
        }
    },


    # --------------------------------------
    # GET BOOKING DETAILS
    # --------------------------------------

    {
        "type": "function",
        "function": {
            "name": "get_booking_details",
            "description": """
Get details of an existing room booking.

Use this when the student asks:
- Show my booking
- What is my booking?
- Check booking HALL-0001
- What room did I book?
""",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_id": {
                        "type": "string",
                        "description": "Booking ID such as HALL-0001"
                    }
                },
                "required": ["booking_id"]
            }
        }
    },


    # --------------------------------------
    # CANCEL BOOKING
    # --------------------------------------

    {
        "type": "function",
        "function": {
            "name": "cancel_room_booking",
            "description": """
Cancel an existing room booking.

Use this only when the student explicitly
asks to cancel a booking.
""",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_id": {
                        "type": "string",
                        "description": "Booking ID such as HALL-0001"
                    }
                },
                "required": ["booking_id"]
            }
        }
    }

]


# ==========================================
# EXECUTE TOOLS
# ==========================================

def execute_tool(tool_name, arguments):

    if tool_name == "search_campus_location":

        return search_campus_location(
            arguments["name"]
        )


    elif tool_name == "get_student_timetable":

        return get_student_timetable(
            arguments["student_id"],
            arguments["day"]
        )


    elif tool_name == "check_room_availability":

        return check_room_availability(
            arguments["booking_date"],
            arguments["start_time"],
            arguments["end_time"]
        )


    elif tool_name == "book_room":

        return book_room(
            arguments["student_id"],
            arguments["room_name"],
            arguments["booking_date"],
            arguments["start_time"],
            arguments["end_time"],
            arguments["purpose"]
        )


    elif tool_name == "get_booking_details":

        return get_booking_details(
            arguments["booking_id"]
        )


    elif tool_name == "cancel_room_booking":

        return cancel_room_booking(
            arguments["booking_id"]
        )


    return {
        "error": f"Unknown tool: {tool_name}"
    }


# ==========================================
# AI AGENT
# ==========================================

def ask_agent(user_message):
    if client is None:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not configured. "
            "Add it to the local .env file before using the AI agent."
        )

    # Save user message
    add_message(
        "user",
        user_message
    )


    # ==========================================
    # SYSTEM PROMPT
    # ==========================================

    system_prompt = f"""
You are an AI Campus Assistant.

You help students with:

1. Campus locations
2. Student timetable
3. Classroom and seminar hall availability
4. Room booking
5. Booking details
6. Booking cancellation


CURRENT STUDENT:

Student ID: 101
Name: Bharathi
Department: CSE
Year: 3
Section: A


TIMETABLE RULES:

If the user says:

"show timetable"
"show the timetable"
"show my timetable"
"full timetable"
"complete timetable"
"weekly timetable"
"all days"
"all the day"

call get_student_timetable with:

student_id = 101
day = "all"


If the user asks for a particular day,
use that day.


If the user says:

"today timetable"
"today's timetable"

today is {datetime.now().strftime("%A")}.

Therefore use:

student_id = 101
day = "{datetime.now().strftime("%A")}"


LOCATION RULE:

Use search_campus_location when
the student asks where something is.

Do not invent campus information.


ROOM BOOKING RULES:

First check room availability.

Do NOT book immediately.

Ask the student to select a room.

Before calling book_room,
the student must explicitly confirm the booking.


BOOKING DETAILS:

Use get_booking_details when
the student gives a booking ID.


CANCELLATION:

Use cancel_room_booking when
the student explicitly asks to cancel.


Always give simple and clear answers.
Never return "None" as an answer.
"""


    messages = [

        {
            "role": "system",
            "content": system_prompt
        }

    ]


    # Add conversation memory
    messages.extend(
        get_memory()
    )


    # ==========================================
    # AGENT LOOP
    # ==========================================

    while True:

        response = client.chat.completions.create(

            model="openai/gpt-4o-mini",

            messages=messages,

            tools=tools,

            tool_choice="auto",

            max_tokens=500
        )


        message = response.choices[0].message


        # ==========================================
        # NO TOOL CALL
        # ==========================================

        if not message.tool_calls:

            answer = message.content

            if answer is None:

                answer = "Sorry, I could not generate a response."


            add_message(
                "assistant",
                answer
            )

            return answer


        # ==========================================
        # ASSISTANT TOOL CALL MESSAGE
        # ==========================================

        messages.append({

            "role": "assistant",

            "content": message.content,

            "tool_calls": [

                {
                    "id": tool_call.id,

                    "type": "function",

                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments
                    }
                }

                for tool_call in message.tool_calls
            ]

        })


        # ==========================================
        # EXECUTE EACH TOOL
        # ==========================================

        for tool_call in message.tool_calls:

            tool_name = tool_call.function.name

            print(
                f"\n[Using tool: {tool_name}]"
            )


            # --------------------------------------
            # SAFE JSON PARSING
            # --------------------------------------

            try:

                arguments = json.loads(
                    tool_call.function.arguments
                )

            except json.JSONDecodeError as e:

                print(
                    "\nTool JSON error:",
                    e
                )

                print(
                    "Arguments:",
                    repr(
                        tool_call.function.arguments
                    )
                )

                return (
                    "Sorry, I could not understand "
                    "the tool request."
                )


            # --------------------------------------
            # RUN TOOL
            # --------------------------------------

            result = execute_tool(
                tool_name,
                arguments
            )


            print(
                "[Tool result]:",
                result
            )


            # --------------------------------------
            # SEND RESULT BACK TO AI
            # --------------------------------------

            messages.append({

                "role": "tool",

                "tool_call_id": tool_call.id,

                "content": json.dumps(
                    result
                )

            })

            # and generates the final answer.


# Production web/API agent. Unlike the legacy CLI above, this graph has no
# keyword router: OpenRouter chooses tools using native function calling.
def _schema(name):
    return {"type": "function", "function": {"name": name,
        "description": f"Use {name} for the selected college. Return only verified data with sources.",
        "parameters": {"type": "object", "properties": {
            "college_id": {"type": "integer"}, "name": {"type": "string"},
            "department": {"type": "string"}, "section": {"type": "string"},
            "semester": {"type": "integer"}, "day": {"type": "string"},
            "query": {"type": "string"}, "level": {"type": "string", "enum": ["UG", "PG", "PhD"]}, "location_name": {"type": "string"},
            "source_location": {"type": "string"}, "destination_location": {"type": "string"},
            "hostel_name": {"type": "string"}, "room_type": {"type": "string"},
            "gender": {"type": "string"}, "degree": {"type": "string"},
            "event_type": {"type": "string"}, "academic_year": {"type": "string"}
        }, "required": ["college_id"]}}}


PRIMARY_TOOLS = [_schema(n) for n in PRIMARY_TOOL_NAMES]


def _run_primary(name, args):
    funcs = {
        "search_college_information": lambda: search_college_information(args["college_id"], args.get("query", "college")),
        "search_departments": lambda: search_departments(args["college_id"], args.get("query", "department")),
        "search_courses_programs": lambda: search_courses_programs(args["college_id"], args.get("query", "course"), args.get("level")),
        "search_admission_information": lambda: search_admission_information(args["college_id"], args.get("query", "admission")),
        "search_college_facilities": lambda: search_college_facilities(args["college_id"], args.get("query", "facility")),
        "search_campus_location": lambda: search_campus_location_for_college(args["college_id"], args.get("name", "")),
        "search_college_contacts": lambda: search_college_contacts(args["college_id"], args.get("query", "contact")),
        "search_college_announcements": lambda: search_college_announcements(args["college_id"], args.get("query")),
        "search_academic_information": lambda: search_academic_information(args["college_id"], args.get("query", "academic")),
        "get_college_official_urls": lambda: get_college_official_urls(args["college_id"]),
    }
    return funcs[name]()


def _resolve_college(user_message, default_college_id):
    message = user_message.lower()
    conn = get_connection()
    rows = conn.execute("SELECT id, short_name, name FROM colleges WHERE is_active=1").fetchall()
    conn.close()
    for row in rows:
        if row["short_name"].lower() in message or row["name"].lower() in message:
            return row["id"]
    aliases = {
        "college of engineering guindy": "CEG",
        "madras institute of technology chennai": "MIT",
        "alaguappa college of technology": "ACT",
        "alagappa college of technology": "ACT",
        "school of architecture and planning": "SAP",
    }
    for alias, short_name in aliases.items():
        if alias in message:
            return next(row["id"] for row in rows if row["short_name"] == short_name)
    return default_college_id


def _direct_tool_request(message):
    text = message.lower()
    has = lambda *words: any(re.search(r"\b" + re.escape(word) + r"\b", text) for word in words)
    is_plain_college_request = text.strip().endswith(" college") and not has(
        "course", "courses", "corse", "corses", "program", "department",
        "facility", "facilities", "admission", "map", "location", "where",
    )
    if "official website" in text or "official url" in text or "official link" in text or "college link" in text or is_plain_college_request:
        return "get_college_official_urls", {}
    if has("map", "where is", "location", "located"):
        location_terms = ("seminar hall", "library", "laboratory", "lab", "building", "block", "location", "located", "map")
        return "search_campus_location", {
            "name": next((term for term in location_terms if term in text), text)
        }
    if has("building", "library", "laboratory", "block", "seminar hall"):
        location_terms = ("seminar hall", "library", "laboratory", "lab", "building", "block", "location", "located", "map")
        return "search_campus_location", {
            "name": next((term for term in location_terms if term in text), text)
        }
    if has("department", "departments", "branch", "branches"):
        return "search_departments", {"query": "department"}
    if has("course", "courses", "corse", "corses", "coruse", "coruses",
           "program", "programs", "programme", "programmes",
           "offering", "offerings", "offered",
           "syllabus", "curriculum", "degree",
           "ug", "pg", "btech", "mtech", "b.tech", "m.tech", "b.e", "m.e", "ph.d"):
        return "search_courses_programs", {"query": text, "level": "PG" if has("pg", "postgraduate", "post graduate") else "UG" if has("ug", "undergraduate") else None}
    if has("admission", "admissions", "eligibility", "apply"):
        return "search_admission_information", {"query": text}
    if has("facility", "facilities", "hostel", "canteen", "laboratory"):
        return "search_college_facilities", {"query": text}
    if has("contact", "phone", "email", "address"):
        return "search_college_contacts", {"query": text}
    if has("announcement", "announcements", "notice", "news", "update"):
        return "search_college_announcements", {"query": text}
    if has("academic", "semester", "exam", "regulation", "calendar"):
        return "search_academic_information", {"query": text}
    return "search_college_information", {"query": text}


def _direct_answer(tool_name, result):
    collections = {
        "search_college_information": ("information", "official college information"),
        "search_departments": ("departments", "departments"),
        "search_courses_programs": ("courses", "courses and programs"),
        "search_admission_information": ("admissions", "admission information"),
        "search_college_facilities": ("facilities", "facilities"),
        "search_campus_location": ("locations", "campus locations"),
        "search_college_contacts": ("contacts", "college contacts"),
        "search_college_announcements": ("announcements", "announcements"),
        "search_academic_information": ("academic_information", "academic information"),
    }
    if tool_name == "get_college_official_urls":
        website = result.get("official_website")
        if not website:
            return "I couldn't find an official website in the available campus sources."
        return f"The official {result.get('college', 'college')} website is available in the links below."
    key, label = collections[tool_name]
    values = result.get(key) or []
    if not values:
        if tool_name == "search_courses_programs":
            return "I couldn't find a course record in the local index yet. Please use the official course sources below."
        return f"I couldn't find that {label} in the available official campus sources."
    if tool_name == "search_courses_programs" and result.get("course_levels"):
        college = None
        if result.get("college_id"):
            source = _college_source(result["college_id"])
            college = source["short_name"] if source else None
        sections = []
        requested_level = result.get("requested_level")
        levels = {
            section: courses for section, courses in result["course_levels"].items()
            if not requested_level or requested_level.lower() in section.lower()
        }
        if requested_level and not levels:
            return f"I could not find verified {requested_level} course information on the available official sources."
        for section, courses in levels.items():
            lines = "\n".join(f"{index}. {course}" for index, course in enumerate(courses, 1))
            sections.append(f"{section}\n{lines}")
        heading = f"Courses offered at {college}" if college else "Courses offered"
        return heading + "\n\n" + "\n\n".join(sections)
    if tool_name == "search_courses_programs" and result.get("course_retrieval_incomplete"):
        return (
            "I could not verify a complete college-specific course list from the available "
            "official pages. Please use the official course sources below."
        )
    if tool_name == "search_courses_programs" and result.get("course_names"):
        college = None
        if result.get("college_id"):
            source = _college_source(result["college_id"])
            college = source["short_name"] if source else None
        heading = f"Courses offered at {college}" if college else "Courses offered"
        course_lines = "\n".join(
            f"{index}. {course}" for index, course in enumerate(result["course_names"], 1)
        )
        return f"{heading}\n\nPrograms and courses\n{course_lines}"
    snippets = []
    irrelevant_terms = (
        "alumni", "alumnus", "convocation", "chairman", "governor",
        "biography", "born in", "schooling", "doctoral studies",
        "commentator", "copyright", "history", "historical",
    )
    category_noise = {
        "search_college_facilities": ("agni", "he has", "curriculum", "distance education", "university industry", "academics"),
        "search_campus_location": ("department", "engineering", "academic", "examination", "workshop", "programme", "course"),
        "search_courses_programs": (
            "convocation", "chairman", "governor", "biography", "he has",
            "he graduated", "after graduating", "received", "contributed",
            "born in", "first institution", "workshop", "notification",
            "scholarship", "programme at", "academic calendar", "academics",
            " from ", " mr.", " mr ", " ms.", " she ", " he ",
            "swayam", "certificate course", "faculty development",
            "student skill", "petronas", "international admissions",
            "admission", "department of", "ayyala",
        ),
    }
    link_terms = {
        "search_courses_programs": ("course", "courses", "program", "programme", "programmes", "prospectus", "degree", "ug", "pg", "b.e", "b.tech", "m.e", "m.tech", "ph.d"),
        "search_college_facilities": ("library", "sports", "hostel", "health", "canteen", "laboratory", "lab", "auditorium", "gym", "research facilities"),
        "search_campus_location": ("library", "location", "located", "campus", "map", "building", "landmark", "address"),
        "search_departments": ("department", "faculty", "school", "branch"),
        "search_admission_information": ("admission", "application", "fee", "eligibility"),
        "search_college_contacts": ("contact", "phone", "email", "address", "office"),
        "search_college_announcements": ("announcement", "news", "notice", "event", "circular"),
        "search_academic_information": ("academic", "calendar", "regulation", "syllabus", "examination"),
    }.get(tool_name, ())
    for value in values:
        content = value.get("content") or value.get("description") or value.get("title")
        if content:
            fragments = [fragment.strip() for fragment in str(content).split("|")]
            for fragment in fragments:
                clean = " ".join(fragment.split())
                text_without_urls = re.sub(r"https?://\S+", "", clean).strip(" :-")
                matches_topic = not link_terms or any(term in clean.lower() for term in link_terms)
                is_irrelevant = any(term in clean.lower() for term in irrelevant_terms)
                is_category_noise = any(term in clean.lower() for term in category_noise.get(tool_name, ()))
                if tool_name == "search_courses_programs" and clean.lower().startswith(("mr.", "mr ", "ms.", "ms ")):
                    is_category_noise = True
                minimum_length = 8 if tool_name == "search_courses_programs" else 40
                if not clean.startswith("%PDF") and len(text_without_urls) >= minimum_length and matches_topic and not is_irrelevant and not is_category_noise:
                    snippets.append(f"- {clean[:350]}")
    if tool_name == "search_campus_location":
        location_evidence = ("address", "located", "chennai", "tamil nadu", "chromepet", "campus location", "library")
        snippets = [snippet for snippet in snippets if any(term in snippet.lower() for term in location_evidence)]
    elif tool_name == "search_college_facilities":
        facility_evidence = ("library", "laboratory", "lab", "hostel", "sports", "canteen", "health", "research facilities", "computing centre")
        snippets = [
            snippet for snippet in snippets
            if any(term in snippet.lower() for term in facility_evidence)
            and "academic calendar" not in snippet.lower()
        ]
    if not snippets:
        for value in values:
            relevant_links = []
            for link in value.get("links") or []:
                link_label = " ".join((link.get("text") or "").split())
                if link_label and (not link_terms or any(term in link_label.lower() for term in link_terms)) and link_label not in relevant_links:
                    relevant_links.append(f"- {link_label}: {link.get('url')}")
            snippets.extend(relevant_links)
    snippets = list(dict.fromkeys(snippets))
    if snippets:
        college = None
        if result.get("college_id"):
            source = _college_source(result["college_id"])
            college = source["short_name"] if source else None
        if tool_name == "search_courses_programs":
            heading = f"Courses offered at {college}" if college else "Courses offered"
        else:
            heading = f"Here is the official information I found about {college} {label}" if college else f"Here is the official information I found about {label}"
        answer = heading + ":\n" + "\n".join(snippets)
        return answer
    return f"I found {len(values)} {label} record(s) in the available official campus sources."


def ask_agent_for_college(user_message, college_id, history=None):
    global client
    effective_college_id = _resolve_college(user_message, college_id)
    tool_name, arguments = _direct_tool_request(user_message)
    result = _run_primary(tool_name, {"college_id": effective_college_id, **arguments})
    if tool_name == "search_courses_programs":
        result["requested_level"] = arguments.get("level")
    if tool_name != "search_college_information" or not os.getenv("OPENROUTER_ENABLE_GENERAL_CHAT"):
        return {
            "answer": _direct_answer(tool_name, result),
            "tool_used": tool_name,
            "sources": result.get("sources", []),
        }
    try:
        api_key = _configured_api_key()
    except RuntimeError as exc:
        return {"answer": str(exc), "tool_used": None, "sources": []}
    if api_key is None:
        return {"answer": "AI service is not configured. Please set OPENROUTER_API_KEY.", "tool_used": None, "sources": []}
    if client is None or client.api_key != api_key:
        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    from langgraph.graph import StateGraph, START, END
    from typing import TypedDict, Any
    class State(TypedDict):
        messages: list
        tool_used: str | None
        sources: list
    graph = StateGraph(State)
    initial = list(history or []) + [{"role": "user", "content": user_message}]
    def agent_node(state):
        response = client.chat.completions.create(
            model=os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini"),
            messages=[{"role": "system", "content": "You are a college assistant. Never invent facts; cite source URLs."}] + state["messages"],
            tools=PRIMARY_TOOLS, tool_choice="auto")
        m = response.choices[0].message
        return {"messages": state["messages"] + [{"role": "assistant", "content": m.content or "", "tool_calls": [
            {"id": c.id, "type": "function", "function": {"name": c.function.name, "arguments": c.function.arguments}} for c in (m.tool_calls or [])]}],
            "tool_used": m.tool_calls[0].function.name if m.tool_calls else state.get("tool_used")}
    def tools_node(state):
        import json
        last = state["messages"][-1]
        additions, sources = [], list(state.get("sources", []))
        for call in last.get("tool_calls", []):
            args = json.loads(call["function"]["arguments"])
            result = _run_primary(call["function"]["name"], args)
            additions.append({"role": "tool", "tool_call_id": call["id"], "content": json.dumps(result)})
            sources.extend(result.get("sources", []))
        return {"messages": state["messages"] + additions, "sources": sources}
    def route(state):
        return "tools" if state["messages"][-1].get("tool_calls") else END
    graph.add_node("agent", agent_node); graph.add_node("tools", tools_node)
    graph.add_edge(START, "agent"); graph.add_conditional_edges("agent", route, {"tools": "tools", END: END}); graph.add_edge("tools", "agent")
    try:
        result = graph.compile().invoke({"messages": initial, "tool_used": None, "sources": []})
    except AuthenticationError:
        return {
            "answer": (
                "OpenRouter authentication failed. Check OPENROUTER_API_KEY "
                "in .env and replace it with a valid, active key."
            ),
            "tool_used": None,
            "sources": [],
        }
    answer = result["messages"][-1].get("content", "I could not generate a response.")
    return {"answer": answer, "tool_used": result.get("tool_used"), "sources": result.get("sources", [])}
