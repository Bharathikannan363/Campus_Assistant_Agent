"""Automated tests for SSRF validation, HTML extraction, college detection, live scraping, and lack of permanent storage."""

from unittest.mock import MagicMock, patch
import pytest
import requests

from web_tools import (
    is_safe_url,
    detect_college,
    extract_page_content,
    fetch_webpage,
    search_college_website,
)
from database import get_connection


def test_ssrf_blocking_localhost():
    """Verify localhost is strictly blocked."""
    safe, err = is_safe_url("http://localhost:8000")
    assert safe is False
    assert "blocked for security" in err


def test_ssrf_blocking_loopback_ip():
    """Verify 127.0.0.1 is blocked."""
    safe, err = is_safe_url("http://127.0.0.1:5000/admin")
    assert safe is False
    assert "blocked for security" in err


def test_ssrf_blocking_private_ip():
    """Verify private subnet (RFC 1918) URLs are blocked."""
    safe, err = is_safe_url("http://192.168.1.1/router")
    assert safe is False
    assert "forbidden" in err


def test_ssrf_unsafe_schemes():
    """Verify file:// and gopher:// schemes are rejected."""
    safe, err = is_safe_url("file:///etc/passwd")
    assert safe is False
    assert "Unsupported scheme" in err


def test_safe_public_url():
    """Verify standard public domain is permitted."""
    safe, err = is_safe_url("https://mitindia.edu")
    assert safe is True
    assert err is None


def test_college_recognition():
    """Verify recognition of college names and aliases."""
    assert detect_college("What courses are at MIT?") == "MIT"
    assert detect_college("Tell me about CEG Guindy campus") == "CEG"
    assert detect_college("Alagappa College of Technology programs") == "ACT"
    assert detect_college("School of Architecture and Planning events") == "SAP"
    assert detect_college("General query about weather") is None


def test_html_extraction():
    """Verify extraction of title, headings, text, tables, and links."""
    sample_html = """
    <html>
        <head><title>Test Campus Page</title></head>
        <body>
            <script>alert('bad');</script>
            <h1>Engineering Programs</h1>
            <p>We offer undergraduate and postgraduate courses in computer science.</p>
            <table>
                <tr><th>Course</th><th>Duration</th></tr>
                <tr><td>B.E. CSE</td><td>4 Years</td></tr>
            </table>
            <a href="https://example.com/admissions">Admissions Portal</a>
        </body>
    </html>
    """
    extracted = extract_page_content(sample_html, url="https://example.com")
    assert extracted["title"] == "Test Campus Page"
    assert "Engineering Programs" in extracted["headings"]
    assert any("computer science" in p for p in extracted["paragraphs"])
    assert any("B.E. CSE | 4 Years" in t for t in extracted["tables"])
    assert any("Admissions Portal" in l["text"] for l in extracted["links"])
    assert "bad" not in extracted["text"]  # Script tag decomposed


def test_fetch_webpage_mocked_success():
    """Verify on-demand live fetching with mocked HTTP response."""
    mock_resp = MagicMock()
    mock_resp.is_redirect = False
    mock_resp.status_code = 200
    mock_resp.headers = {"content-type": "text/html; charset=utf-8", "content-length": "500"}
    mock_resp.encoding = "utf-8"
    mock_resp.iter_content.return_value = [b"<html><head><title>Official College</title></head><body><h1>Department of Computing</h1><p>Our department provides world class education.</p></body></html>"]

    with patch("web_tools.is_safe_url", return_value=(True, None)):
        with patch("requests.get", return_value=mock_resp):
            page = fetch_webpage("https://example-college.edu/computing")
            assert page["success"] is True
            assert page["title"] == "Official College"
            assert "Department of Computing" in page["headings"]


def test_fetch_webpage_timeout_handling():
    """Verify timeout is caught and reported gracefully."""
    with patch("web_tools.is_safe_url", return_value=(True, None)):
        with patch("requests.get", side_effect=requests.exceptions.Timeout("Connection timed out")):
            page = fetch_webpage("https://slow-college.edu/admissions")
            assert page["success"] is False
            assert "timed out" in page["error"].lower()


def test_fetch_webpage_http_error():
    """Verify HTTP errors (404/500) are handled without unhandled exceptions."""
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    http_err = requests.exceptions.HTTPError(response=mock_resp)

    with patch("web_tools.is_safe_url", return_value=(True, None)):
        with patch("requests.get", side_effect=http_err):
            page = fetch_webpage("https://example-college.edu/notfound")
            assert page["success"] is False
            assert "HTTP error" in page["error"]


def test_ssrf_redirect_to_private_ip_blocked():
    """Verify that a redirect hop targeting a private IP address is rejected."""
    redirect_resp = MagicMock()
    redirect_resp.is_redirect = True
    redirect_resp.status_code = 302
    redirect_resp.headers = {"Location": "http://192.168.1.1/internal"}

    with patch("requests.get", return_value=redirect_resp):
        page = fetch_webpage("https://mitindia.edu/redirect")
        assert page["success"] is False
        assert "redirect blocked" in page["error"].lower()


def test_no_permanent_storage_in_sqlite():
    """Verify that live scraping NEVER inserts scraped content into SQLite database tables."""
    conn = get_connection()
    # Check that rag_chunks and scraped_pages are empty or not populated by scraping
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM rag_chunks")
    initial_chunks = cursor.fetchone()[0]

    # Run live search and scrape
    res = search_college_website("courses offered at MIT", college="MIT")
    assert res["success"] is True

    # Confirm database was NOT populated
    cursor.execute("SELECT COUNT(*) FROM rag_chunks")
    after_chunks = cursor.fetchone()[0]
    conn.close()

    assert initial_chunks == after_chunks == 0
