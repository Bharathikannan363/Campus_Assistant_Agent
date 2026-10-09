# AI Campus Assistant Agent

> **An intelligent, conversational campus assistant with native tool-calling, autonomous web scraping, session memory, and SQLite database integration.**

---

## 1. Project Overview

The **AI Campus Assistant Agent** allows students to interact naturally with campus systems to:
* **Lookup Campus Locations:** Find classrooms, laboratories, buildings, departments, and landmarks across the campus.
* **View Student Timetables:** Retrieve schedules for today, tomorrow, specific weekdays, or full week overviews.
* **Check Facility Availability:** Query real-time availability for classrooms and seminar halls with $[start, end)$ half-open interval checking.
* **Book & Manage Rooms:** Create reservations with explicit student confirmation, retrieve booking details, and cancel bookings with ownership authorization.
* **Autonomous College Web Research:** Discover and scrape official university pages (CEG, MIT, ACT, SAP) for courses, programs, departments, and admissions, with verified source citations.
* **Context-Aware Memory:** Retain active college context and multi-turn conversational history with student isolation.
* **Interactive Terminal & Web Interfaces:** Run either a lightweight terminal CLI or a full FastAPI web server.

---

## 2. Architecture & Modular Structure

```text
campus-assistant/
│
├── main.py                # Terminal interactive interface & entry point (with --serve flag)
├── agent.py               # LLM integration, tool schemas, bounded execution loop, error recovery
├── database.py            # SQLite schema initialization, connection management, queries
├── memory.py              # Session memory, college context tracking, pending booking state
├── campus_tools.py        # Location lookup, synonym matching, multi-match resolution
├── timetable_tools.py     # Student timetable lookup, relative day resolution (timezone-aware)
├── booking_tools.py       # Availability checks, 24-hr time normalization, conflict prevention
├── web_tools.py           # DuckDuckGo search, SSRF security guard, HTML parser, source citations
├── config.py              # Environment variable loading, secure logging, configuration status
├── models.py              # Structured ToolResult and domain dataclasses
├── rag.py                 # Overlapping chunking, grounded metadata storage, and scoring
├── api.py                 # FastAPI REST API endpoints & JWT authentication
├── requirements.txt       # Python project dependencies
├── .env.example           # Documented environment variable template
├── .gitignore             # Git ignore rules (protects .env, logs, test databases)
│
├── data/
│   └── campus.db          # Production SQLite database (intact and preserved)
│
├── tests/
│   ├── conftest.py        # Isolated test database fixture
│   ├── test_agent.py      # Tool dispatch, API error recovery, iteration limits
│   ├── test_booking.py    # Time normalization, collision logic, authorized cancellation
│   ├── test_database.py   # Connection, foreign keys, student lookup
│   ├── test_memory.py     # Sliding window, context retention, session isolation
│   ├── test_timetable.py  # Specific weekdays, relative days, invalid student handling
│   └── test_web_tools.py  # SSRF protection, college detection, HTML extraction
│
└── docs/
    ├── architecture.md    # Detailed system architecture, workflows, mermaid diagrams
    ├── setup.md           # Setup and execution guide for Windows PowerShell
    └── test_report.md     # Academic project report and 37-case testing matrix
```

---

## 3. Quick Start

### 3.1 Prerequisites
* Python 3.10+ (Tested on Python 3.14.6)
* Windows PowerShell or Linux/macOS shell

### 3.2 Installation
```powershell
# 1. Navigate to directory
cd C:\Users\KF_20\Desktop\project\Campus-Assistant-Agent

# 2. Activate virtual environment
.\venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
Copy-Item .env.example .env
```



---

## 4. Running the Assistant

### Option A: Interactive Terminal Interface (CLI)
```powershell
python main.py
```
```text
========================================
       AI CAMPUS ASSISTANT AGENT
========================================

Ask a question about your campus.
Type 'help' for commands.
Type 'exit' to stop.

You: Where is the Computer Networks Lab?
Assistant: The Computer Networks Lab is located in the CS Block on the 2nd floor, room CS-204 (Near Main Library).

You: Show my timetable for today
Assistant: Here is your timetable for today (Friday):
1. Artificial Intelligence (10:00 AM) - Room: AI-302
2. Database Lab (2:00 PM) - Room: IT-101

You: What courses are offered at MIT?
Assistant: Here are the courses offered at the Madras Institute of Technology (MIT):
...
Sources:
- MIT Official Website (https://mitindia.edu/)
- Anna University (https://www.annauniv.edu/)
```

**Commands inside CLI:**
* `help` — Show available commands and sample prompts.
* `status` — View active model, API status, and remembered college context.
* `clear` — Clear conversation memory.
* `serve` — Launch the web application.
* `exit` — Exit the terminal shell.

### Option B: FastAPI Web Portal
```powershell
python main.py --serve
```
* **Frontend Web UI:** `http://127.0.0.1:8000`
* **Swagger API Docs:** `http://127.0.0.1:8000/docs`

---

## 5. Running Automated Tests

Run the complete test suite:
```powershell
pytest tests/ -v
```
**Result:** 41 passed in ~7.3s against isolated test database.

---

## 6. Security, Privacy & Ephemeral Scraping Controls
* **Live Ephemeral Retrieval:** Public college web scraping is purely on-demand in temporary memory for the active request. Scraped text, extracted HTML, and course lists are **never** stored in SQLite, disk files, permanent caches, or vector databases.
* **Separation of Concerns:** SQLite is strictly reserved for operational campus data (`students`, `locations`, `timetable`, `rooms`, `bookings`). Web scraping is solely for external public institutional information.
* **Content Discard & Log Safety:** Temporary scraped content is discarded after the response is generated. Webpage contents are never logged.
* **SSRF & Redirect Guard:** Validates URLs and each redirect hop; blocks requests to `localhost`, loopback IPs, private subnets (RFC 1918), and link-local cloud metadata endpoints (`169.254.169.254`).
* **Resource Limits:** Hard 15-second request timeouts, 2 MB download size limit, and per-domain rate limiting.
* **Strict Time Interval Math:** Normalizes all times to 24-hr format and applies $[start, end)$ half-open interval math, preventing overlapping bookings.
* **Authorization Verification:** Only the booking owner or authorized student can view private records or cancel reservations.
* **No Secret Leaks:** Configuration validation suppresses API key printing in logs, exceptions, or terminal output.

---

## 7. Documentation
* [Architecture Guide](docs/architecture.md) — Workflows, tool registry, and mermaid diagrams.
* [Setup Guide](docs/setup.md) — Step-by-step installation instructions.
* [Technical & Test Report](docs/test_report.md) — Academic report with methodology, objectives, and test matrix.
