"""Automated tests for conversation memory, context tracking, and session isolation."""

from memory import (
    SessionMemory,
    get_session,
    add_message,
    get_memory,
    clear_memory,
    set_current_college,
    get_current_college,
)


def test_session_message_addition():
    """Verify storing and retrieving conversation messages."""
    session = SessionMemory(session_id="test_msg", max_messages=5)
    session.add_message("user", "Hello")
    session.add_message("assistant", "Hi there!")

    messages = session.get_messages()
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"


def test_session_sliding_window():
    """Verify that memory respects max_messages and drops oldest messages."""
    session = SessionMemory(session_id="test_slide", max_messages=3)
    session.add_message("user", "Message 1")
    session.add_message("assistant", "Message 2")
    session.add_message("user", "Message 3")
    session.add_message("assistant", "Message 4")

    messages = session.get_messages()
    assert len(messages) == 3
    assert messages[0]["content"] == "Message 2"
    assert messages[2]["content"] == "Message 4"


def test_college_context_tracking():
    """Verify remembering and clearing active college context."""
    session = SessionMemory(session_id="test_college")
    assert session.get_college() is None

    session.set_college("MIT")
    assert session.get_college() == "MIT"

    session.set_college("CEG")
    assert session.get_college() == "CEG"

    session.clear()
    assert session.get_college() is None


def test_multi_session_isolation():
    """Verify that different sessions do not leak data across students."""
    session_a = get_session("student_101")
    session_b = get_session("student_102")

    session_a.clear()
    session_b.clear()

    session_a.add_message("user", "Question from 101")
    session_a.set_college("MIT")

    session_b.add_message("user", "Question from 102")
    session_b.set_college("ACT")

    assert session_a.get_messages()[0]["content"] == "Question from 101"
    assert session_a.get_college() == "MIT"

    assert session_b.get_messages()[0]["content"] == "Question from 102"
    assert session_b.get_college() == "ACT"


def test_pending_booking_state():
    """Verify tracking pending booking parameters."""
    session = SessionMemory(session_id="test_booking_state")
    session.update_pending_booking(room_name="Seminar Hall 1", date="2026-10-25")

    state = session.get_pending_booking()
    assert state["room_name"] == "Seminar Hall 1"
    assert state["date"] == "2026-10-25"

    session.clear_pending_booking()
    assert session.get_pending_booking() == {}
