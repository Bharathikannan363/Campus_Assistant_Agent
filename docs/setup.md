# AI Campus Assistant Agent — Setup and Installation Guide

This document provides step-by-step instructions to set up, configure, and execute the AI Campus Assistant Agent on Windows systems using PowerShell.

---

## 1. Prerequisites

* **Operating System:** Windows 10/11
* **Python:** Python 3.10 to 3.14 (Verified on Python 3.14.6)
* **Shell:** Windows PowerShell or Command Prompt
* **Internet Connection:** Required for OpenRouter LLM API calls and live web scraping.

---

## 2. Environment Setup

### Step 2.1: Clone or Open Project Directory

Open Windows PowerShell and navigate to the project directory:

```powershell
cd C:\Users\KF_20\Desktop\project\Campus-Assistant-Agent
```

### Step 2.2: Create and Activate Virtual Environment

Create a clean virtual environment:

```powershell
python -m venv venv
```

Activate the virtual environment:

```powershell
.\venv\Scripts\Activate.ps1
```

*(Note: If script execution is restricted, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in your PowerShell window).*

### Step 2.3: Install Dependencies

Install all core, web-scraping, and testing dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

---

## 3. Configuration (`.env`)

Copy `.env.example` to create your local `.env` file:

```powershell
Copy-Item .env.example .env
```

Edit `.env` using your preferred editor:

```env
# OpenRouter API Key (Format: sk-or-v1-...)
OPENROUTER_API_KEY=sk-or-v1-your_actual_key_here

# Model Selection (Configurable; defaults to openai/gpt-4o-mini)
OPENROUTER_MODEL=openai/gpt-4o-mini

# Web Search Provider (duckduckgo, tavily, serpapi)
SEARCH_PROVIDER=duckduckgo
SEARCH_API_KEY=

# Campus & Assistant Defaults
CAMPUS_TIMEZONE=Asia/Kolkata
DEFAULT_STUDENT_ID=101

# API Secret
JWT_SECRET=your-random-production-secret
```

> [!IMPORTANT]
> Never commit your `.env` file or API keys to version control. The `.gitignore` file is configured to exclude all `.env` files.

---

## 4. Database Initialization

The SQLite database (`campus.db`) is automatically initialized upon startup. To manually re-initialize or verify the database tables:

```powershell
python -c "import database; database.create_database(); database.create_legacy_database()"
```

This verifies the creation of:
* `students`, `locations`, `timetable`, `rooms`, `bookings`
* `colleges`, `users`, `campus_locations`, `timetables`, `hostels`, `announcements`, `courses`, `scraped_pages`, `rag_chunks`, `conversations`, `messages`, `web_cache`

---

## 5. Running the Application

### 5.1 Terminal Interface (Standard Application Mode)

To start the interactive terminal campus assistant:

```powershell
python main.py
```

Expected startup prompt:
```text
========================================
       AI CAMPUS ASSISTANT AGENT
========================================

Ask a question about your campus.
Type 'help' for commands.
Type 'exit' to stop.

You:
```

#### Terminal Commands:
* `help` — View sample questions and system guidance.
* `status` — View active model, API configuration, and college context.
* `clear` — Reset conversation history and college context.
* `serve` — Launch the FastAPI web portal.
* `exit` — Exit the assistant gracefully.

### 5.2 FastAPI Web Portal & UI Mode

To start the FastAPI web server directly:

```powershell
python main.py --serve
# or
uvicorn api:app --host 127.0.0.1 --port 8000
```

* **Web UI:** Open your browser to `http://127.0.0.1:8000`
* **Interactive API Documentation:** Open `http://127.0.0.1:8000/docs`

---

## 6. Running Automated Tests

Run the full automated test suite using `pytest`:

```powershell
pytest tests/ -v
```

To run a specific test category:
```powershell
# Run only booking interval tests
pytest tests/test_booking.py -v

# Run only web tools and SSRF tests
pytest tests/test_web_tools.py -v

# Run only agent tool loop tests
pytest tests/test_agent.py -v
```

All tests execute against an isolated temporary test database and mock external web servers without altering production data.
