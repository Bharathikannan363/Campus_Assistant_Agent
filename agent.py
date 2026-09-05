import os
import json
<<<<<<< HEAD
from pathlib import Path
=======
>>>>>>> a4ba3ffd78a2334c89d1d74c49eb8148af132b8e

from memory import add_message, get_memory

from dotenv import load_dotenv
from openai import OpenAI

from tools import (
    search_campus_location,
    get_student_timetable,
    check_room_availability,
    book_room,
    get_booking_details,
    cancel_room_booking
)
<<<<<<< HEAD
from tools import (
    PRIMARY_TOOL_NAMES, search_campus_location_for_college,
    get_student_timetable_for_college, check_hostel_availability,
    get_hostel_room_detail, search_college_announcements, search_college_events,
    search_course_in_college, get_academic_calendar, college_map
)
=======
>>>>>>> a4ba3ffd78a2334c89d1d74c49eb8148af132b8e


# ==========================================
# LOAD API KEY
# ==========================================

<<<<<<< HEAD
ENV_FILE = Path(__file__).with_name(".env")


def _api_key():
    load_dotenv(dotenv_path=ENV_FILE, override=False)
    return os.getenv("OPENROUTER_API_KEY", "").strip()
=======
load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY")

if not api_key:
    print("API key not found!")
    exit()
>>>>>>> a4ba3ffd78a2334c89d1d74c49eb8148af132b8e


# ==========================================
# OPENROUTER
# ==========================================

<<<<<<< HEAD
api_key = _api_key()
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key) if api_key else None
=======
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key
)
>>>>>>> a4ba3ffd78a2334c89d1d74c49eb8148af132b8e


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

    # Save user message
    add_message(
        "user",
        user_message
    )


    # ==========================================
    # SYSTEM PROMPT
    # ==========================================

    system_prompt = """
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

today is Saturday.

Therefore use:

student_id = 101
day = "Saturday"


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

            model="openai/gpt-5",

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

        # The while loop now continues.
        # The AI receives the tool result
<<<<<<< HEAD
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
            "query": {"type": "string"}, "location_name": {"type": "string"},
            "source_location": {"type": "string"}, "destination_location": {"type": "string"},
            "hostel_name": {"type": "string"}, "room_type": {"type": "string"},
            "gender": {"type": "string"}, "degree": {"type": "string"},
            "event_type": {"type": "string"}, "academic_year": {"type": "string"}
        }, "required": ["college_id"]}}}


PRIMARY_TOOLS = [_schema(n) for n in PRIMARY_TOOL_NAMES]


def _run_primary(name, args):
    funcs = {
        "search_campus_location": lambda: search_campus_location_for_college(args["college_id"], args.get("name", "")),
        "get_student_timetable": lambda: get_student_timetable_for_college(args["college_id"], args.get("department"), args.get("section"), args.get("semester"), day=args.get("day")),
        "check_hostel_availability": lambda: check_hostel_availability(args["college_id"], args.get("hostel_name"), args.get("gender"), args.get("room_type")),
        "get_hostel_room_detail": lambda: get_hostel_room_detail(args["college_id"], args.get("hostel_name"), args.get("room_type")),
        "search_college_announcements": lambda: search_college_announcements(args["college_id"], args.get("query")),
        "search_college_events": lambda: search_college_events(args["college_id"], args.get("query"), event_type=args.get("event_type")),
        "search_course_in_college": lambda: search_course_in_college(args["college_id"], args.get("name"), args.get("degree"), args.get("department"), args.get("query")),
        "get_academic_calendar": lambda: get_academic_calendar(args["college_id"], args.get("academic_year"), args.get("semester")),
        "college_map": lambda: college_map(args["college_id"], args.get("location_name"), args.get("source_location"), args.get("destination_location")),
    }
    return funcs[name]()


def ask_agent_for_college(user_message, college_id, history=None):
    global client
    api_key = _api_key()
    if not api_key:
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
    result = graph.compile().invoke({"messages": initial, "tool_used": None, "sources": []})
    answer = result["messages"][-1].get("content", "I could not generate a response.")
    return {"answer": answer, "tool_used": result.get("tool_used"), "sources": result.get("sources", [])}
=======
        # and generates the final answer.
>>>>>>> a4ba3ffd78a2334c89d1d74c49eb8148af132b8e
