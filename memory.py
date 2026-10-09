"""Conversation memory and state management for AI Campus Assistant.

Maintains:
- Session-isolated conversation history with a sliding window
- Contextual college tracking (for follow-ups like 'Courses')
- Active task and pending room booking slot filling
- Clean context reset and multi-student isolation
"""

from typing import Any, Dict, List, Optional
import time


class SessionMemory:
    """Encapsulates conversational context for an individual session/student."""

    def __init__(self, session_id: str = "default", max_messages: int = 20):
        self.session_id = session_id
        self.max_messages = max_messages
        self.history: List[Dict[str, str]] = []
        self.current_college: Optional[str] = None
        self.active_task: Optional[str] = None
        self.pending_booking: Dict[str, Any] = {}
        self.last_activity: float = time.time()

    def add_message(self, role: str, content: str) -> None:
        """Append a message to the session history, respecting window limits."""
        self.history.append({"role": role, "content": content})
        if len(self.history) > self.max_messages:
            # Always preserve system prompt if present at index 0, or slide
            self.history = self.history[-self.max_messages:]
        self.last_activity = time.time()

    def get_messages(self) -> List[Dict[str, str]]:
        """Return shallow copy of session history messages."""
        return list(self.history)

    def set_college(self, college: Optional[str]) -> None:
        """Update the currently discussed college context."""
        if college:
            self.current_college = college.upper().strip()
        else:
            self.current_college = None
        self.last_activity = time.time()

    def get_college(self) -> Optional[str]:
        """Retrieve current college context."""
        return self.current_college

    def update_pending_booking(self, **kwargs) -> Dict[str, Any]:
        """Update slots for an active room booking flow."""
        self.active_task = "room_booking"
        self.pending_booking.update(kwargs)
        self.last_activity = time.time()
        return dict(self.pending_booking)

    def get_pending_booking(self) -> Dict[str, Any]:
        """Retrieve pending booking parameters."""
        return dict(self.pending_booking)

    def clear_pending_booking(self) -> None:
        """Reset pending booking state once complete or cancelled."""
        self.pending_booking.clear()
        if self.active_task == "room_booking":
            self.active_task = None
        self.last_activity = time.time()

    def clear(self) -> None:
        """Clear all conversation history and state for this session."""
        self.history.clear()
        self.current_college = None
        self.active_task = None
        self.pending_booking.clear()
        self.last_activity = time.time()


# Session registry for multi-user isolation
_sessions: Dict[str, SessionMemory] = {}


def get_session(session_id: str = "default") -> SessionMemory:
    """Get or create session memory instance."""
    if session_id not in _sessions:
        _sessions[session_id] = SessionMemory(session_id=session_id)
    return _sessions[session_id]


# Backward-compatible module functions
def add_message(role: str, content: str, session_id: str = "default") -> None:
    get_session(session_id).add_message(role, content)


def get_memory(session_id: str = "default") -> List[Dict[str, str]]:
    return get_session(session_id).get_messages()


def clear_memory(session_id: str = "default") -> None:
    get_session(session_id).clear()


def set_current_college(college: Optional[str], session_id: str = "default") -> None:
    get_session(session_id).set_college(college)


def get_current_college(session_id: str = "default") -> Optional[str]:
    return get_session(session_id).get_college()