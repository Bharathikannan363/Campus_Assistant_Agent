# AI Campus Assistant Agent — Technical & Test Report

---

## Academic & Project Report Sections

### Abstract
Modern higher education campuses present complex informational ecosystems encompassing disparate schedules, distributed facilities, administrative regulations, and published academic curriculums. Navigating these resources often burdens students and administrative staff. This project presents the **AI Campus Assistant Agent**, an intelligent, conversational system equipped with natural-language understanding, native function calling, dynamic official website scraping, session-isolated memory, and transactional database integrity. Operating in both an interactive terminal shell and a RESTful web interface, the system seamlessly answers academic queries, displays student timetables, checks facility availability, atomically executes seminar room bookings with explicit confirmation, and retrieves verified, cited information from official university portals.

### 1. Introduction
University campuses are characterized by dense administrative infrastructures where students frequently require immediate answers to location, timetable, booking, and curriculum inquiries. Existing solutions commonly rely on static FAQs or keyword-based search bars that cannot interpret conversational context or take transactional actions. The AI Campus Assistant Agent bridges this gap by marrying Large Language Models (LLMs) with an extensible tool registry, SQLite relational databases, and an SSRF-safe web retrieval engine.

### 2. Problem Statement
Traditional campus systems face several acute limitations:
1. **Siloed Data:** Facility reservations, timetable schedules, and institutional course lists reside in separate databases or static PDF/HTML web portals.
2. **Brittle Interfaces:** Students must consult separate websites and manually cross-reference room schedules or timetables.
3. **Hallucination Risk:** Standard AI chatbots hallucinate nonexistent campus rooms, schedules, and false web URLs when ungrounded.
4. **Concurrency Vulnerabilities:** Naive reservation systems frequently suffer from double bookings when concurrent users reserve overlapping intervals.

### 3. Objectives
The core objectives of the AI Campus Assistant Agent are:
* Provide natural-language comprehension via OpenAI-compatible OpenRouter APIs.
* Enforce native function calling so actions (booking, schedule lookup, search) are executed deterministically against verified backends.
* Implement robust reservation validation using normalized 24-hour time and half-open interval collision detection $[start, end)$.
* Ground external web inquiries in real-time scraped content with mandatory source citations.
* Protect against Server-Side Request Forgery (SSRF) and data leakage through strict URL parsing and multi-student session isolation.
* Provide an interactive terminal interface alongside a production-ready FastAPI web service.

### 4. Existing System vs. Proposed System

| Feature | Existing Baseline System | Proposed AI Campus Assistant Agent |
| :--- | :--- | :--- |
| **Interface** | Unconfigured web endpoint / script | Dedicated terminal CLI (`main.py`) + REST API (`api.py`) |
| **Tool Calling** | Fragmented, hardcoded string checks | Native tool schema registry with validated parameters |
| **Web Research** | Fixed site crawl without SSRF checks | Live DuckDuckGo provider + SSRF-safe scraper + source citations |
| **Room Booking** | Buggy 12-hr AM/PM string comparison (caused double bookings) | 24-hr time normalization + $[start, end)$ half-open interval collision check + atomic transactions |
| **Timetable** | Static day matching (failed on 'today'/'tomorrow') | Timezone-aware relative day resolution + weekday overview |
| **Memory** | Unisolated global message list | Decoupled `SessionMemory` with sliding window, college context retention, and pending booking slots |
| **Testing** | 0 automated tests | 37 automated tests across 6 modules with 100% pass rate |

### 5. Methodology & Architecture
The system adopts a modular Agent-Tool architecture:
1. **Intent Analysis & Routing:** The agent analyzes user intent and decides whether to respond conversationally or invoke one or more tools from the tool registry.
2. **Tool Execution Layer:** Structured Python modules (`campus_tools.py`, `timetable_tools.py`, `booking_tools.py`, `web_tools.py`) perform validated queries against SQLite or external websites.
3. **Safety & Grounding:** Tool outputs return structured `ToolResult` objects containing data and source URLs. The model synthesizes the final response strictly grounded in this evidence.

---

## 6. Automated Testing Results & Verification

All automated tests were executed using `pytest` within an isolated virtual environment (`Python 3.14.6`) against a dedicated test database (`test_campus.db`).

### Test Summary
* **Total Tests:** 41
* **Passed:** 41 (100%)
* **Failed:** 0
* **Execution Time:** ~7.3 seconds

### Detailed Test Matrix

| Test Suite | Test Case Name | Description & Precondition | Expected Result | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Agent** | `test_execute_tool_location` | Query known location (CN Lab) | Returns building CS Block, room CS-204 | Match confirmed | **PASS** |
| | `test_execute_tool_timetable` | Query Monday timetable for ID 101 | Returns 2 scheduled courses | 2 courses returned | **PASS** |
| | `test_execute_tool_web_search` | Query courses at MIT | Returns success=True with official sources | Match confirmed | **PASS** |
| | `test_execute_tool_unknown` | Execute nonexistent tool | Returns graceful error dictionary without crash | Graceful error returned | **PASS** |
| | `test_agent_missing_api_key` | Unset `OPENROUTER_API_KEY` | Informs user of configuration issue | Error message returned | **PASS** |
| | `test_agent_auth_error` | Simulate 401 AuthenticationError | Returns authentication advisory | Handled gracefully | **PASS** |
| | `test_agent_tool_loop_execution` | Multi-turn tool execution simulation | Executes tool and generates grounded response | Completed 2 turns | **PASS** |
| **Booking** | `test_time_normalization` | Normalize 10:00 AM, 2 PM, 14:00 | Standardizes to 24-hr `HH:MM` format | All normalized | **PASS** |
| | `test_invalid_time_format` | Pass invalid hour `25:00` | Raises ValueError | ValueError raised | **PASS** |
| | `test_interval_overlap_logic` | Half-open intervals [10, 12) vs [11, 13) | Detects overlap; allows adjacent [10, 11) & [11, 12) | Overlap evaluated correctly | **PASS** |
| | `test_check_availability_empty_day` | Check availability on unreserved date | Both Seminar Hall 1 & 2 returned | Available list returned | **PASS** |
| | `test_book_room_and_detect_conflict` | Book 10:00-12:00, then attempt 11:00-13:00 | Overlapping booking rejected with conflict message | Overlap rejected | **PASS** |
| | `test_booking_invalid_time_order` | Attempt booking with start > end (3 PM to 2 PM) | Rejected with time order error | Order error caught | **PASS** |
| | `test_booking_authorization_cancellation` | Student 102 attempts to cancel 101's booking | Blocked with Unauthorized error | Blocked correctly | **PASS** |
| **Database** | `test_database_connection` | Verify foreign keys enabled | PRAGMA foreign_keys == 1 | Verified enabled | **PASS** |
| | `test_student_lookup` | Query existing student 101 | Returns Bharathi (CSE) | Match confirmed | **PASS** |
| | `test_missing_student_lookup` | Query nonexistent student 9999 | Returns None | None returned | **PASS** |
| | `test_locations_query` | Query total locations count | Count >= 2 | Count verified | **PASS** |
| **Memory** | `test_session_message_addition` | Add user and assistant messages | Stored in history in correct order | Order verified | **PASS** |
| | `test_session_sliding_window` | Add 4 messages to window of size 3 | Oldest message dropped, newest 3 kept | Window enforced | **PASS** |
| | `test_college_context_tracking` | Set college to MIT, then clear | Context tracked and cleared | Verified | **PASS** |
| | `test_multi_session_isolation` | Independent students (101 and 102) | Memories and college context completely isolated | Isolation verified | **PASS** |
| | `test_pending_booking_state` | Store partial booking slots | Updated and cleared atomically | State preserved | **PASS** |
| **Timetable** | `test_timetable_specific_weekday` | Query Monday timetable | 2 classes returned | Match confirmed | **PASS** |
| | `test_timetable_all_days` | Query weekly timetable | Full week entries returned | Match confirmed | **PASS** |
| | `test_timetable_no_classes_day` | Query Sunday schedule | Returns clear 'No classes found' message | Message returned | **PASS** |
| | `test_timetable_relative_day_resolution` | Resolve 'today' and 'tomorrow' | Resolves to current weekday dynamically | Valid weekday | **PASS** |
| | `test_timetable_nonexistent_student` | Query non-existent student 9999 | Returns student not found error | Error returned | **PASS** |
| | `test_timetable_invalid_student_id` | Query string ID 'not_an_id' | Returns invalid ID error | Error returned | **PASS** |
| **Web Tools** | `test_ssrf_blocking_localhost` | Request `http://localhost:8000` | Blocked for security | Blocked | **PASS** |
| | `test_ssrf_blocking_loopback_ip` | Request `http://127.0.0.1:5000` | Blocked for security | Blocked | **PASS** |
| | `test_ssrf_blocking_private_ip` | Request `http://192.168.1.1` | Blocked private IP subnet | Blocked | **PASS** |
| | `test_ssrf_unsafe_schemes` | Request `file:///etc/passwd` | Blocked unsupported scheme | Blocked | **PASS** |
| | `test_safe_public_url` | Request `https://mitindia.edu` | Approved as safe public URL | Approved | **PASS** |
| | `test_college_recognition` | Detect college in queries | Recognizes CEG, MIT, ACT, SAP | All matched | **PASS** |
| | `test_html_extraction` | Parse mock HTML with script and tables | Strips script, extracts tables and links | Clean data extracted | **PASS** |
| | `test_fetch_webpage_mocked_success` | Live on-demand fetch with mock HTML | Extracts title, headings without disk storage | Extracted cleanly | **PASS** |
| | `test_fetch_webpage_timeout_handling` | Simulate 15s request timeout | Catches Timeout and returns graceful error | Handled gracefully | **PASS** |
| | `test_fetch_webpage_http_error` | Simulate HTTP 404/500 error | Catches HTTPError and returns status | Handled gracefully | **PASS** |
| | `test_ssrf_redirect_to_private_ip_blocked` | Redirect hop targeting 192.168.1.1 | Blocks redirect hop before request | Redirect blocked | **PASS** |
| | `test_no_permanent_storage_in_sqlite` | Run search & scrape and check DB | 0 records inserted into SQLite; purely ephemeral | 0 records in SQLite | **PASS** |

---

## 7. Limitations & Edge Cases
1. **Dynamic Client-Side Single Page Apps (SPAs):** Pages rendered purely with client-side JavaScript frameworks (React/Vue without SSR) may yield incomplete text without a headless browser.
2. **Third-Party Anti-Bot Measures:** Institutional portals that employ aggressive Cloudflare or CAPTCHA defenses may temporarily reject automated web requests.
3. **Public Academic Sources:** Certain campus resources (such as private hostel rosters or internal faculty grade books) are behind authenticated intranets and intentionally inaccessible.

## 8. Future Enhancements
* **Multimodal Image Maps:** Integrate visual campus maps with routing path overlays for indoor navigation.
* **Push Notifications:** Webhook and email alerts for timetable schedule changes or booking confirmations.
* **Vector Embeddings:** Ingest syllabi and institutional handbooks into local dense vector indexes (e.g. FAISS/Chroma) for deeper semantic RAG search.

## 9. Conclusion
The AI Campus Assistant Agent successfully achieves all architectural and operational goals. By replacing brittle keyword routers with native LLM tool execution, implementing interval-safe reservation logic, and enforcing strict SSRF web scraping protections, the system delivers a reliable, production-ready, academic-grade conversational assistant.
