"""Automated tests for agent tool routing, error recovery, and loop mechanics."""

import json
from unittest.mock import MagicMock, patch
import pytest

from agent import ask_agent, execute_tool, MAX_TOOL_ITERATIONS
from memory import clear_memory


def test_execute_tool_location():
    """Verify tool dispatcher executes search_campus_location."""
    res = execute_tool("search_campus_location", {"name": "Computer Networks Lab"})
    assert "building" in res
    assert res["building"] == "CS Block"


def test_execute_tool_timetable():
    """Verify tool dispatcher executes get_student_timetable."""
    res = execute_tool("get_student_timetable", {"student_id": 101, "day": "Monday"})
    assert isinstance(res, list)
    assert len(res) == 2


def test_execute_tool_web_search():
    """Verify tool dispatcher executes search_college_website."""
    res = execute_tool("search_college_website", {"query": "courses", "college": "MIT"})
    assert res["success"] is True
    assert "sources" in res


def test_execute_tool_unknown():
    """Verify unknown tool returns error structure without crashing."""
    res = execute_tool("nonexistent_tool", {})
    assert "error" in res
    assert "Unknown tool" in res["error"]


def test_agent_missing_api_key(monkeypatch):
    """Verify helpful error returned when OPENROUTER_API_KEY is unset."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    res = ask_agent("Hello", session_id="test_no_key")
    assert "Configuration Error" in res


def test_agent_auth_error():
    """Verify graceful handling when OpenRouter throws AuthenticationError."""
    from openai import AuthenticationError
    import httpx

    fake_request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
    fake_response = httpx.Response(401, request=fake_request)

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = AuthenticationError(
        message="Invalid API Key", response=fake_response, body=None
    )

    with patch("agent.get_client", return_value=mock_client):
        res = ask_agent("Hello", session_id="test_auth_err")
        assert "Authentication Error" in res


def test_agent_tool_loop_execution():
    """Verify that agent detects tool call, executes tool, and returns final answer."""
    # Step 1: Model requests tool
    tool_call_mock = MagicMock()
    tool_call_mock.id = "call_abc123"
    tool_call_mock.function.name = "search_campus_location"
    tool_call_mock.function.arguments = json.dumps({"name": "Computer Networks Lab"})

    msg1 = MagicMock()
    msg1.content = None
    msg1.tool_calls = [tool_call_mock]
    choice1 = MagicMock()
    choice1.message = msg1
    resp1 = MagicMock()
    resp1.choices = [choice1]

    # Step 2: Model returns final text
    msg2 = MagicMock()
    msg2.content = "The Computer Networks Lab is in the CS Block, room CS-204."
    msg2.tool_calls = None
    choice2 = MagicMock()
    choice2.message = msg2
    resp2 = MagicMock()
    resp2.choices = [choice2]

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [resp1, resp2]

    with patch("agent.get_client", return_value=mock_client):
        clear_memory("test_loop")
        answer = ask_agent("Where is Computer Networks Lab?", session_id="test_loop")
        assert "CS Block" in answer
        assert mock_client.chat.completions.create.call_count == 2
