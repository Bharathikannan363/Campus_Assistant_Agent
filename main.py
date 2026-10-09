"""Terminal-based entry point for the AI Campus Assistant Agent.

Features:
- Interactive conversational shell with rich formatting
- Helpful system commands (help, exit, clear, status, serve)
- Safe error handling without raw stack traces
- Context management and clean exits
"""

import sys
import logging
from config import validate_config, get_model, get_campus_timezone, get_default_student_id
from memory import clear_memory, get_current_college, get_memory
from agent import ask_agent

BANNER = """========================================
       AI CAMPUS ASSISTANT AGENT
========================================

Ask a question about your campus.
Type 'help' for commands.
Type 'exit' to stop.
"""

HELP_TEXT = """
Available Commands:
  help       - Show this guidance message
  exit, quit - Exit the campus assistant
  clear      - Clear the current conversation history and context
  status     - Show current agent configuration and active context
  serve      - Start the FastAPI web application and UI

Sample Questions You Can Ask:
  * "Where is the Computer Networks Lab?"
  * "Show my timetable for today."
  * "What classes do I have on Monday?"
  * "Is Seminar Hall 1 available tomorrow from 10:00 AM to 12:00 PM?"
  * "Book Seminar Hall 1 tomorrow from 10:00 AM to 12:00 PM for project review."
  * "What courses are offered at MIT?"
  * "Tell me about CEG campus."
"""


def print_status(session_id: str = "cli"):
    """Display current system status and memory state."""
    config = validate_config()
    college = get_current_college(session_id)
    history_len = len(get_memory(session_id))

    print("\n--- System Status ---")
    print(f"  Model:            {config['model']}")
    print(f"  API Configured:   {'Yes' if config['api_key_configured'] else 'No (Missing Key)'}")
    print(f"  Search Provider:  {config['search_provider']}")
    print(f"  Timezone:         {config['timezone']}")
    print(f"  Student ID:       {config['default_student_id']}")
    print(f"  College Context:  {college or 'None (will detect from query)'}")
    print(f"  Messages Stored:  {history_len}")
    print("---------------------\n")


def run_cli():
    """Run interactive terminal session."""
    session_id = "cli"
    print(BANNER)

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye! Have a great day on campus.")
            break

        if not user_input:
            continue

        lowered = user_input.lower()

        if lowered in ("exit", "quit", "q"):
            print("\nGoodbye! Have a great day on campus.")
            break

        elif lowered == "help":
            print(HELP_TEXT)
            continue

        elif lowered in ("clear", "reset"):
            clear_memory(session_id)
            print("\n[Conversation context and memory cleared.]\n")
            continue

        elif lowered == "status":
            print_status(session_id)
            continue

        elif lowered == "serve":
            print("\nStarting Web Application at http://127.0.0.1:8000 ...")
            import uvicorn
            uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=False)
            break

        # Process user request through agent
        try:
            print("\nAssistant:")
            response = ask_agent(user_input, session_id=session_id)
            print(response)
            print()
        except Exception as exc:
            logging.getLogger("campus_assistant").exception("CLI error occurred")
            print(f"\nSorry, an error occurred while processing your request: {str(exc)}\n")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("--serve", "--web"):
        import uvicorn
        uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=False)
    else:
        run_cli()
