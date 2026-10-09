"""AI Campus Assistant Agent.

Integrates OpenRouter with OpenAI-compatible client, multi-turn tool execution loop,
bounded iterations, robust error handling, session memory, and college grounding.
"""

import json
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI, APIError, AuthenticationError, APITimeoutError, APIConnectionError

from config import get_api_key, get_model, get_campus_timezone, get_default_student_id
from memory import (
    add_message,
    get_memory,
    get_session,
    set_current_college,
    get_current_college,
)
from tools import (
    search_campus_location,
    get_student_timetable,
    check_room_availability,
    book_room,
    get_booking_details,
    cancel_room_booking,
    search_college_website,
    fetch_webpage,
    detect_college,
    SUPPORTED_COLLEGES,
)

logger = logging.getLogger("campus_assistant.agent")

# Maximum iterations in a single agent turn to avoid infinite loops
MAX_TOOL_ITERATIONS = 5

# ==========================================
# OPENAI / OPENROUTER CLIENT
# ==========================================

def get_client() -> Optional[OpenAI]:
    """Obtain configured OpenAI client pointing to OpenRouter."""
    api_key = get_api_key()
    if not api_key:
        return None
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        timeout=30.0,
    )


# Client instance for direct imports
client = get_client()


# ==========================================
# TOOL DEFINITIONS (OpenAI Tool Calling Schema)
# ==========================================

tools = [
    {
        "type": "function",
        "function": {
            "name": "search_campus_location",
            "description": "Find a campus location, classroom, lab, building, or landmark. Use when the student asks 'Where is X?', 'Where is the lab?', or asks for all locations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the campus location, lab, building, room, or 'all' to list all locations."
                    }
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_student_timetable",
            "description": "Get the student's timetable. Default student ID is 101. Supports 'today', 'tomorrow', a specific weekday (Monday-Sunday), or 'all' for weekly overview.",
            "parameters": {
                "type": "object",
                "properties": {
                    "student_id": {
                        "type": "integer",
                        "description": "Student ID (default: 101)."
                    },
                    "day": {
                        "type": "string",
                        "description": "Day name (Monday, Tuesday, ...), 'today', 'tomorrow', or 'all' for the whole week."
                    }
                },
                "required": ["student_id", "day"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_room_availability",
            "description": "Check which seminar halls or classrooms are available for a particular date and interval. MUST be called BEFORE booking.",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_date": {
                        "type": "string",
                        "description": "Booking date in YYYY-MM-DD format (e.g. '2026-10-15'), 'today', or 'tomorrow'."
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Starting time such as '10:00 AM', '2 PM', or '14:00'."
                    },
                    "end_time": {
                        "type": "string",
                        "description": "Ending time such as '12:00 PM', '4 PM', or '16:00'."
                    }
                },
                "required": ["booking_date", "start_time", "end_time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "book_room",
            "description": "Reserve a seminar hall or classroom. ONLY call this after availability has been checked and the student has EXPLICITLY confirmed the booking.",
            "parameters": {
                "type": "object",
                "properties": {
                    "student_id": {
                        "type": "integer",
                        "description": "Student ID (default: 101)."
                    },
                    "room_name": {
                        "type": "string",
                        "description": "Room name such as 'Seminar Hall 1' or 'Seminar Hall 2'."
                    },
                    "booking_date": {
                        "type": "string",
                        "description": "Booking date in YYYY-MM-DD, 'today', or 'tomorrow'."
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Starting time such as '10:00 AM' or '14:00'."
                    },
                    "end_time": {
                        "type": "string",
                        "description": "Ending time such as '12:00 PM' or '16:00'."
                    },
                    "purpose": {
                        "type": "string",
                        "description": "Purpose of reservation."
                    }
                },
                "required": ["student_id", "room_name", "booking_date", "start_time", "end_time", "purpose"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_booking_details",
            "description": "Retrieve details of an existing room booking by booking ID (e.g. HALL-0001).",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_id": {
                        "type": "string",
                        "description": "Booking ID such as HALL-0001."
                    }
                },
                "required": ["booking_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_room_booking",
            "description": "Cancel an existing room booking with student authorization. Only call when the student explicitly requests cancellation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_id": {
                        "type": "string",
                        "description": "Booking ID such as HALL-0001."
                    },
                    "student_id": {
                        "type": "integer",
                        "description": "Requesting student ID for authorization check (default: 101)."
                    }
                },
                "required": ["booking_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_college_website",
            "description": "Search official college websites (CEG, MIT, ACT, SAP) for courses, programs, departments, admissions, faculty, facilities, or general information. Ground answers with source URLs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query such as 'courses offered at MIT' or 'departments in CEG'."
                    },
                    "college": {
                        "type": "string",
                        "description": "College abbreviation if known (CEG, MIT, ACT, SAP)."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_webpage",
            "description": "Safely fetch and extract text from an official college URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Public HTTP or HTTPS webpage URL."
                    }
                },
                "required": ["url"]
            }
        }
    }
]


# ==========================================
# TOOL DISPATCHER
# ==========================================

def execute_tool(tool_name: str, arguments: Dict[str, Any], session_id: str = "default") -> Dict[str, Any]:
    """Execute the selected tool with validated arguments."""
    try:
        if tool_name == "search_campus_location":
            return search_campus_location(arguments.get("name", ""))

        elif tool_name == "get_student_timetable":
            sid = arguments.get("student_id", get_default_student_id())
            day = arguments.get("day", "today")
            return get_student_timetable(sid, day)

        elif tool_name == "check_room_availability":
            return check_room_availability(
                arguments["booking_date"],
                arguments["start_time"],
                arguments["end_time"],
            )

        elif tool_name == "book_room":
            sid = arguments.get("student_id", get_default_student_id())
            return book_room(
                sid,
                arguments["room_name"],
                arguments["booking_date"],
                arguments["start_time"],
                arguments["end_time"],
                arguments.get("purpose", "Academic Discussion"),
            )

        elif tool_name == "get_booking_details":
            sid = arguments.get("student_id", get_default_student_id())
            return get_booking_details(arguments["booking_id"], student_id=sid)

        elif tool_name == "cancel_room_booking":
            sid = arguments.get("student_id", get_default_student_id())
            return cancel_room_booking(arguments["booking_id"], student_id=sid)

        elif tool_name == "search_college_website":
            query = arguments.get("query", "")
            college = arguments.get("college")
            # If no college supplied, use remembered college
            if not college:
                college = get_current_college(session_id)
            res = search_college_website(query, college=college)
            if res.get("short_name"):
                set_current_college(res["short_name"], session_id)
            return res

        elif tool_name == "fetch_webpage":
            return fetch_webpage(arguments["url"])

        return {"error": f"Unknown tool: '{tool_name}'."}

    except KeyError as e:
        return {"error": f"Missing required parameter '{e.args[0]}' for tool '{tool_name}'."}
    except Exception as e:
        logger.exception(f"Error executing tool {tool_name}")
        return {"error": f"Tool execution failed: {str(e)}"}


# ==========================================
# SYSTEM PROMPT BUILDER
# ==========================================

def build_system_prompt(college_context: Optional[str] = None) -> str:
    today_name = datetime.now().strftime("%A")
    college_hint = f"\nACTIVE COLLEGE CONTEXT: {college_context}" if college_context else ""

    return f"""You are the AI Campus Assistant Agent for students.

RESPONSIBILITIES:
1. Campus locations, classrooms, labs, buildings, and landmarks (search_campus_location).
2. Student timetables for today, tomorrow, specific weekdays, or full week (get_student_timetable).
3. Seminar hall and classroom availability checking (check_room_availability).
4. Room reservations with explicit student confirmation (book_room).
5. Retrieving booking details and authorized cancellations (get_booking_details, cancel_room_booking).
6. Official college web research for CEG, MIT, ACT, and SAP (search_college_website).

CURRENT STUDENT PROFILE:
Student ID: 101
Name: Bharathi
Department: CSE
Year: 3, Section: A
Today is: {today_name}
{college_hint}

OPERATIONAL GUIDELINES:
- Always use the tools to retrieve actual data. Never fabricate timetable, booking, or web results.
- For timetable questions:
  * 'today' or 'today timetable' -> get_student_timetable(student_id=101, day='today')
  * 'tomorrow timetable' -> get_student_timetable(student_id=101, day='tomorrow')
  * 'all' or 'weekly' -> get_student_timetable(student_id=101, day='all')
- For room booking:
  * ALWAYS check availability first using check_room_availability.
  * Present available options and ask the student to confirm.
- For public college information (courses, departments, faculty, professors, laboratories, libraries, admissions, fees):
  * Automatically call search_college_website with the query.
  * If the student asks for a specific laboratory, facility, or campus location not in the local database, search official college web sources.
  * ALWAYS cite the official source URLs provided by the tool under a 'Sources:' heading.
  * Scraped information is provided on-demand for this answer; ground your answer on the retrieved evidence.
- If a tool returns an error or no records, communicate this politely to the student without crashing.
- Never return 'None'. Give structured, clean, well-formatted markdown answers.
"""


# ==========================================
# MAIN AGENT INTERACTION LOOP
# ==========================================

def ask_agent(user_message: str, session_id: str = "default") -> str:
    """Run agent loop for the terminal assistant with tool execution and memory."""
    llm_client = get_client()
    if llm_client is None:
        return (
            "Configuration Error: OPENROUTER_API_KEY is not configured or missing in .env.\n"
            "Please add a valid OpenRouter API key to your .env file."
        )

    session = get_session(session_id)

    # Detect college in user message and update context
    detected = detect_college(user_message)
    if detected:
        session.set_college(detected)

    # Record user message in memory
    session.add_message("user", user_message)

    # Build prompt and assemble context
    system_prompt = build_system_prompt(session.get_college())
    messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    messages.extend(session.get_messages())

    model_name = get_model()
    iterations = 0

    while iterations < MAX_TOOL_ITERATIONS:
        iterations += 1

        try:
            response = llm_client.chat.completions.create(
                model=model_name,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                max_tokens=600,
            )
        except AuthenticationError:
            err = "Authentication Error: The OpenRouter API key provided is invalid or expired. Check your .env file."
            logger.error(err)
            return err
        except (APITimeoutError, APIConnectionError) as exc:
            err = f"Network Error: Unable to reach OpenRouter API ({str(exc)}). Please check your internet connection."
            logger.error(err)
            return err
        except APIError as exc:
            err = f"API Error: OpenRouter returned an error ({exc.message if hasattr(exc, 'message') else str(exc)})."
            logger.error(err)
            return err
        except Exception as exc:
            err = f"Unexpected Error: {str(exc)}"
            logger.exception("Unexpected LLM error")
            return err

        choice = response.choices[0]
        message = choice.message

        # Case 1: No tool calls made — final answer returned
        if not message.tool_calls:
            answer = message.content or "I processed your request, but have no additional details to share."
            session.add_message("assistant", answer)
            return answer

        # Case 2: Tool calls detected
        # Append assistant message with tool calls to conversation trajectory
        assistant_turn = {
            "role": "assistant",
            "content": message.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in message.tool_calls
            ],
        }
        messages.append(assistant_turn)

        # Execute all tool calls in this turn
        for tc in message.tool_calls:
            tool_name = tc.function.name
            print(f"\n[Tool Execution: {tool_name}]")

            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError as exc:
                logger.warning(f"Malformed tool JSON arguments: {tc.function.arguments} ({exc})")
                tool_result = {"error": f"Invalid JSON arguments: {tc.function.arguments}"}
            else:
                tool_result = execute_tool(tool_name, args, session_id=session_id)

            if tool_name in ("search_college_website", "fetch_webpage"):
                src_count = len(tool_result.get("sources", [])) if isinstance(tool_result, dict) else 0
                print(f"[Result]: Fetched on-demand content from {src_count} official source(s). Scraped content is temporary and discarded after response.")
            else:
                print(f"[Result]: {str(tool_result)[:180]}...")

            # Append tool result to messages
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(tool_result, default=str),
            })

    # If maximum iterations exceeded
    fallback_answer = "I completed several tool lookups, but could not finalize an answer within the iteration limit."
    session.add_message("assistant", fallback_answer)
    return fallback_answer


# ==========================================
# BACKWARD COMPATIBILITY: ask_agent_for_college (for api.py)
# ==========================================

def ask_agent_for_college(user_message: str, college_id: int, history: Optional[List[Any]] = None) -> Dict[str, Any]:
    """Provide structured response for API chat endpoint."""
    college_mapping = {1: "CEG", 2: "MIT", 3: "SAP", 4: "ACT"}
    college_code = college_mapping.get(college_id, "CEG")
    session_id = f"college_api_{college_id}"

    # Set college context
    session = get_session(session_id)
    session.set_college(college_code)

    answer = ask_agent(user_message, session_id=session_id)

    # Extract source URLs if present in answer
    sources = []
    found_urls = re.findall(r"https?://[^\s)\]]+", answer)
    for u in set(found_urls):
        sources.append({"title": "Official Web Source", "url": u})

    return {
        "answer": answer,
        "tool_used": "multi_tool_agent",
        "sources": sources,
    }
