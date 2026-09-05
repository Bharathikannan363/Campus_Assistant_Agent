import os
import json

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


# ==========================================
# LOAD API KEY
# ==========================================

load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY")

if not api_key:
    print("API key not found!")
    exit()


# ==========================================
# OPENROUTER
# ==========================================

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key
)


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
        # and generates the final answer.