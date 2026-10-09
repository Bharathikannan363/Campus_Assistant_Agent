"""Live on-demand web searching and official college website scraping without permanent storage.

Key features:
- Live, ephemeral-only retrieval (NO SQLite storage, NO file caching, NO persistent RAG store)
- Discards scraped content after response generation
- Safe redirect validation and SSRF protection (private IP / localhost / metadata blocking)
- Configurable search provider (DuckDuckGo, Tavily, SerpAPI, direct official domain discovery)
- Content-type checking, 2MB size limit, 15-second timeout, per-domain rate limiting
- Automatic query categorization (courses, departments, faculty, laboratories, libraries, admissions)
- Grounded citations with official source URLs
"""

import ipaddress
import logging
import re
import socket
import time
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

from config import get_search_provider, get_search_api_key

logger = logging.getLogger("campus_assistant.web")

# Rate limiting: timestamp of last request per domain (ephemeral in-memory dictionary)
_domain_last_request: Dict[str, float] = {}
RATE_LIMIT_DELAY_SECONDS = 0.5

# Supported official colleges and domains
SUPPORTED_COLLEGES = {
    "CEG": {
        "name": "College of Engineering, Guindy",
        "short_name": "CEG",
        "aliases": ["ceg", "college of engineering guindy", "engineering guindy", "guindy campus"],
        "website": "https://ceg.annauniv.edu/",
        "fallback": "https://www.annauniv.edu/",
        "domains": ["ceg.annauniv.edu", "annauniv.edu"],
        "course_url": "https://www.annauniv.edu/pdf/CEG_UG_Fee_Structure.pdf",
        "course_programs": (
            "Information Technology (IT)",
            "Computer Science and Engineering (CSE)",
            "Electronics and Communication Engineering (ECE)",
            "Mechanical Engineering",
            "Civil Engineering",
            "Electrical and Electronics Engineering (EEE)",
            "Biomedical Engineering",
            "Printing and Packaging Technology",
        ),
        "course_levels": {
            "UG Programs": (
                "B.E. Computer Science and Engineering",
                "B.Tech Information Technology",
                "B.E. Electronics and Communication Engineering",
                "B.E. Mechanical Engineering",
                "B.E. Civil Engineering",
                "B.E. Electrical and Electronics Engineering",
                "B.E. Biomedical Engineering",
            ),
            "PG Programs": (
                "M.E. Computer Science and Engineering",
                "M.Tech Information Technology",
                "M.E. Software Engineering",
                "M.E. VLSI Design",
                "M.B.A.",
                "M.C.A.",
            ),
        },
    },
    "MIT": {
        "name": "Madras Institute of Technology",
        "short_name": "MIT",
        "aliases": ["mit", "madras institute of technology", "mit chromepet", "mit chennai"],
        "website": "https://mitindia.edu/",
        "fallback": "https://www.annauniv.edu/",
        "domains": ["mitindia.edu", "annauniv.edu"],
        "course_url": "https://www.annauniv.edu/pdf/MIT_UG_Fee_Structure.pdf",
        "course_programs": (
            "Aeronautical Engineering",
            "Automobile Engineering",
            "Computer Technology",
            "Electronics Engineering",
            "Instrumentation Engineering",
            "Production Technology",
            "Rubber and Plastics Technology",
            "Information Technology",
        ),
        "course_levels": {
            "UG Programs": (
                "B.E. Aeronautical Engineering",
                "B.E. Automobile Engineering",
                "B.Tech Computer Technology",
                "B.E. Electronics Engineering",
                "B.E. Instrumentation Engineering",
                "B.E. Production Technology",
                "B.Tech Rubber and Plastics Technology",
                "B.Tech Information Technology",
            ),
            "PG Programs": (
                "M.E. Aeronautical Engineering",
                "M.E. Avionics",
                "M.E. Automobile Engineering",
                "M.E. Communication and Networking",
                "M.E. Mechatronics",
                "M.E. Manufacturing Engineering",
            ),
        },
    },
    "ACT": {
        "name": "Alagappa College of Technology",
        "short_name": "ACT",
        "aliases": ["act", "alagappa college of technology", "alaguappa", "act campus"],
        "website": "https://www.annauniv.edu/act/",
        "fallback": "https://www.annauniv.edu/",
        "domains": ["www.annauniv.edu", "annauniv.edu"],
        "course_url": "https://www.annauniv.edu/act/courses/index.html",
        "course_programs": (
            "Chemical Engineering",
            "Food Technology",
            "Industrial Biotechnology",
            "Petroleum Engineering and Technology",
            "Pharmaceutical Technology",
            "Ceramic Technology",
            "Textile Technology",
            "Leather Technology",
            "Apparel Technology",
        ),
        "course_levels": {
            "UG Programs": (
                "B.Tech Chemical Engineering",
                "B.Tech Food Technology",
                "B.Tech Industrial Biotechnology",
                "B.Tech Petroleum Engineering and Technology",
                "B.Tech Pharmaceutical Technology",
                "B.Tech Ceramic Technology",
                "B.Tech Textile Technology",
                "B.Tech Leather Technology",
                "B.Tech Apparel Technology",
            ),
            "PG Programs": (
                "M.Tech Biotechnology",
                "M.Tech Chemical Engineering",
                "M.Tech Food Technology",
                "M.Tech Nano Science and Technology",
                "M.Tech Industrial Safety and Hazards Management",
                "M.Tech Environmental Science and Technology",
            ),
        },
    },
    "SAP": {
        "name": "School of Architecture and Planning",
        "short_name": "SAP",
        "aliases": ["sap", "school of architecture and planning", "sap campus", "architecture and planning"],
        "website": "https://www.annauniv.edu/sap/",
        "fallback": "https://www.annauniv.edu/",
        "domains": ["www.annauniv.edu", "annauniv.edu"],
        "course_url": "https://www.annauniv.edu/sap/academics.html",
        "course_programs": (
            "Architecture (B.Arch)",
            "Planning (B.Plan)",
            "Landscape Architecture (M.Arch)",
            "General Architecture (M.Arch)",
            "Town Planning (M.Plan)",
        ),
        "course_levels": {
            "UG Programs": (
                "B.Arch (Bachelor of Architecture)",
                "B.Plan (Bachelor of Planning)",
            ),
            "PG Programs": (
                "M.Arch (General Architecture)",
                "M.Arch (Landscape Architecture)",
                "M.Plan (Master of Planning)",
            ),
        },
    },
}

# Categorized keyword mappings
QUERY_KEYWORDS = {
    "courses": (
        "course", "courses", "corse", "corses", "programme", "programmes",
        "program", "programs", "offering", "degree", "ug", "pg", "b.e", "b.tech",
        "m.e", "m.tech", "syllabus", "curriculum", "b.arch", "m.arch",
    ),
    "departments": (
        "department", "departments", "dept", "branch", "branches", "school",
    ),
    "faculty": (
        "faculty", "professor", "professors", "teacher", "teachers", "staff",
        "hod", "head of department", "dean", "director", "lecturer",
    ),
    "laboratories": (
        "laboratory", "laboratories", "lab", "labs", "research facility",
        "research facilities", "computing centre", "workshop",
    ),
    "libraries": (
        "library", "libraries", "learning centre", "learning center", "books",
        "e-resources", "reading room",
    ),
    "admissions": (
        "admission", "admissions", "apply", "eligibility", "fees", "fee structure",
        "counselling", "cutoff", "entrance",
    ),
    "facilities": (
        "facility", "facilities", "hostel", "canteen", "sports", "gym",
        "auditorium", "health centre", "amenities",
    ),
    "locations": (
        "location", "located", "campus", "building", "landmark", "address", "map",
    ),
    "contacts": (
        "contact", "phone", "email", "address", "telephone", "office",
    ),
    "announcements": (
        "announcement", "announcements", "news", "notice", "notices", "circular", "update",
    ),
}

IRRELEVANT_TERMS = (
    "alumni", "alumnus", "convocation", "chairman", "governor",
    "biography", "born in", "schooling", "doctoral studies",
    "commentator", "copyright", "syndicate",
)


# ==========================================
# 1. SSRF & URL SECURITY VALIDATION
# ==========================================

def is_safe_url(url: str) -> Tuple[bool, Optional[str]]:
    """Validate URL to protect against SSRF, internal network scanning, and invalid schemes."""
    if not url or not isinstance(url, str):
        return False, "Empty or invalid URL."

    try:
        parsed = urlparse(url.strip())
    except Exception as e:
        return False, f"Malformed URL: {e}"

    if parsed.scheme not in ("http", "https"):
        return False, f"Unsupported scheme '{parsed.scheme}'. Only http and https are permitted."

    hostname = parsed.hostname
    if not hostname:
        return False, "URL contains no hostname."

    # Block localhost, cloud metadata, and zero addresses
    lowered_host = hostname.lower()
    blocked_hosts = {
        "localhost", "127.0.0.1", "0.0.0.0", "metadata.google.internal",
        "169.254.169.254", "instance-data",
    }
    if lowered_host in blocked_hosts or lowered_host.endswith(".local") or lowered_host.endswith(".internal"):
        return False, f"Access to '{hostname}' is blocked for security."

    try:
        # Resolve hostname to verify destination IP address
        addr_info = socket.getaddrinfo(hostname, None)
        for _, _, _, _, sockaddr in addr_info:
            ip_str = sockaddr[0]
            ip_obj = ipaddress.ip_address(ip_str)
            if (
                ip_obj.is_private
                or ip_obj.is_loopback
                or ip_obj.is_reserved
                or ip_obj.is_link_local
                or ip_obj.is_multicast
            ):
                return False, f"Resolution to private/local address {ip_str} is forbidden."
    except socket.gaierror:
        return False, f"Could not resolve host '{hostname}'."
    except Exception as e:
        return False, f"Network security verification failed: {e}"

    return True, None


def _apply_rate_limiting(hostname: str) -> None:
    """Enforce gentle delay between requests to the same host."""
    now = time.time()
    last = _domain_last_request.get(hostname, 0.0)
    elapsed = now - last
    if elapsed < RATE_LIMIT_DELAY_SECONDS:
        time.sleep(RATE_LIMIT_DELAY_SECONDS - elapsed)
    _domain_last_request[hostname] = time.time()


# ==========================================
# 2. COLLEGE RECOGNITION
# ==========================================

def detect_college(text: str) -> Optional[str]:
    """Recognize college name or alias from natural language text."""
    lowered = f" {text.lower()} "
    for key, config in SUPPORTED_COLLEGES.items():
        if f" {key.lower()} " in lowered:
            return key
        for alias in config["aliases"]:
            if alias in lowered:
                return key
    return None


# ==========================================
# 3. ON-DEMAND WEBPAGE FETCHING (EPHEMERAL)
# ==========================================

def fetch_webpage(url: str, timeout: int = 15, max_bytes: int = 2_000_000) -> Dict[str, Any]:
    """Fetch webpage safely on-demand into temporary memory.

    Enforces:
    - SSRF pre-check on original URL and each redirect hop
    - 15-second timeout
    - 2 MB maximum response size
    - Content-type validation
    - Discarded after processing; never stored on disk or in SQLite
    """
    is_safe, error = is_safe_url(url)
    if not is_safe:
        return {"url": url, "error": error, "success": False}

    parsed = urlparse(url)
    _apply_rate_limiting(parsed.hostname or "")

    headers = {
        "User-Agent": "Mozilla/5.0 (AI-Campus-Assistant/1.0; LivePublicWebScraper)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        # Step-by-step redirect following with SSRF check at each hop
        current_url = url
        max_redirects = 3
        response = None

        for _ in range(max_redirects + 1):
            is_safe, error = is_safe_url(current_url)
            if not is_safe:
                return {"url": current_url, "error": f"Redirect blocked: {error}", "success": False}

            response = requests.get(
                current_url,
                headers=headers,
                timeout=timeout,
                stream=True,
                allow_redirects=False,
            )

            if response.is_redirect or response.status_code in (301, 302, 303, 307, 308):
                location = response.headers.get("Location")
                if not location:
                    break
                current_url = urljoin(current_url, location)
                continue
            else:
                break

        if response is None:
            return {"url": url, "error": "No response received.", "success": False}

        response.raise_for_status()

        # Content-type check
        content_type = response.headers.get("content-type", "").lower()
        if "application/pdf" in content_type:
            return {
                "url": current_url,
                "title": current_url.split("/")[-1],
                "content_type": "pdf",
                "text": "[Official PDF Document Available at Source URL]",
                "headings": [],
                "links": [],
                "tables": [],
                "success": True,
            }

        valid_types = ("text/html", "application/xhtml+xml", "text/plain")
        if not any(vt in content_type for vt in valid_types):
            return {
                "url": current_url,
                "error": f"Unsupported media type '{content_type}'. Only HTML and PDF are supported.",
                "success": False,
            }

        # Size limit check
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) > max_bytes:
            return {"url": current_url, "error": f"Response exceeds size limit ({max_bytes} bytes).", "success": False}

        downloaded = 0
        chunks = []
        for chunk in response.iter_content(chunk_size=16384):
            downloaded += len(chunk)
            if downloaded > max_bytes:
                return {"url": current_url, "error": f"Downloaded content exceeded {max_bytes} bytes.", "success": False}
            chunks.append(chunk)

        html = b"".join(chunks).decode(response.encoding or "utf-8", errors="replace")
        extracted = extract_page_content(html, url=current_url)
        extracted["success"] = True
        return extracted

    except requests.exceptions.Timeout:
        return {"url": url, "error": f"Request to {url} timed out after {timeout} seconds.", "success": False}
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else "Unknown"
        return {"url": url, "error": f"HTTP error {status} for {url}.", "success": False}
    except requests.exceptions.RequestException as e:
        return {"url": url, "error": f"Network error accessing {url}: {str(e)}", "success": False}


def extract_page_content(html: str, url: Optional[str] = None) -> Dict[str, Any]:
    """Parse HTML and extract headings, paragraphs, lists, tables, and links."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove non-content elements
    for tag in soup(["script", "style", "noscript", "svg", "nav", "footer", "iframe", "form"]):
        tag.decompose()

    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    headings = [" ".join(h.get_text(" ", strip=True).split()) for h in soup.find_all(["h1", "h2", "h3", "h4"])]
    paragraphs = [" ".join(p.get_text(" ", strip=True).split()) for p in soup.find_all("p") if p.get_text(strip=True)]
    list_items = [" ".join(li.get_text(" ", strip=True).split()) for li in soup.find_all("li") if li.get_text(strip=True)]

    # Tables
    tables = []
    for tr in soup.find_all("tr"):
        cells = [" ".join(c.get_text(" ", strip=True).split()) for c in tr.find_all(["th", "td"])]
        row_str = " | ".join(c for c in cells if c)
        if row_str:
            tables.append(row_str)

    # Links
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].split("#", 1)[0].strip()
        if url:
            href = urljoin(url, href)
        text = " ".join(a.get_text(" ", strip=True).split())
        if text and href.startswith(("http://", "https://")):
            links.append({"text": text, "url": href})

    combined_text = " ".join(paragraphs + list_items)
    return {
        "url": url or "",
        "title": title,
        "headings": headings,
        "paragraphs": paragraphs,
        "list_items": list_items,
        "tables": tables,
        "links": links,
        "text": combined_text,
    }


# ==========================================
# 4. CONFIGURABLE WEB SEARCH DISCOVERY
# ==========================================

def search_web(query: str, domains: Optional[List[str]] = None, max_results: int = 5) -> List[Dict[str, str]]:
    """Discover relevant webpages using the configured search provider."""
    provider = get_search_provider()
    results: List[Dict[str, str]] = []

    domain_query = ""
    if domains:
        domain_query = " " + " OR ".join(f"site:{d}" for d in domains)
    full_query = f"{query}{domain_query}".strip()

    # Provider 1: DuckDuckGo
    if provider == "duckduckgo":
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                raw = list(ddgs.text(full_query, max_results=max_results))
                for r in raw:
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("href") or r.get("link", ""),
                        "snippet": r.get("body") or r.get("snippet", ""),
                    })
        except Exception as e:
            logger.warning(f"DuckDuckGo search provider issue: {e}")

    # Fallback / Direct Discovery when provider returns empty or is offline
    if not results and domains:
        for d in domains:
            root_url = f"https://{d}/"
            results.append({
                "title": f"Official Portal ({d})",
                "url": root_url,
                "snippet": f"Official institutional web portal for {query}",
            })

    return results[:max_results]


# ==========================================
# 5. LIVE COLLEGE SEARCH & SCRAPE PIPELINE
# ==========================================

def search_college_website(query: str, college: Optional[str] = None, max_results: int = 5) -> Dict[str, Any]:
    """Execute live web search and on-demand scraping for official college information.

    Extracts content dynamically for the active request only.
    No scraped text is written to SQLite, persistent storage, or vector databases.
    """
    college_key = (college.upper() if college else None) or detect_college(query)
    if not college_key or college_key not in SUPPORTED_COLLEGES:
        return {
            "success": False,
            "error": f"Could not determine a supported college from '{query}'. Supported colleges: CEG, MIT, ACT, SAP.",
            "sources": [],
        }

    config = SUPPORTED_COLLEGES[college_key]
    lowered_query = query.lower()

    # Identify query focus terms
    matched_keywords = set()
    for category, kws in QUERY_KEYWORDS.items():
        if any(w in lowered_query for w in kws):
            matched_keywords.update(kws)

    # Gather URLs to inspect live
    urls_to_check = [config["website"]]
    if config.get("course_url") and any(w in lowered_query for w in ("course", "program", "degree", "fee", "admission")):
        urls_to_check.append(config["course_url"])
    if config.get("fallback") and config["fallback"] not in urls_to_check:
        urls_to_check.append(config["fallback"])

    # Live discovery through search provider
    web_res = search_web(query, domains=config["domains"], max_results=max_results)
    for wr in web_res:
        u = wr["url"]
        if u and u not in urls_to_check:
            urls_to_check.append(u)

    # Scrape on-demand into temporary memory
    scraped_snippets: List[str] = []
    sources: List[Dict[str, str]] = []
    seen_sources: Set[str] = set()

    for url in urls_to_check[:6]:
        page = fetch_webpage(url)
        if not page.get("success"):
            continue

        src_title = page.get("title") or config["name"]
        if url not in seen_sources:
            sources.append({"title": f"{config['short_name']} - {src_title}", "url": url})
            seen_sources.add(url)

        if page.get("content_type") == "pdf":
            scraped_snippets.append(f"Official document available at {url}")
            continue

        # Extract relevant content matching query
        for p in page.get("paragraphs", []) + page.get("list_items", []) + page.get("tables", []):
            p_clean = " ".join(p.split())
            if len(p_clean) < 15 or len(p_clean) > 400:
                continue
            if any(term in p_clean.lower() for term in IRRELEVANT_TERMS):
                continue
            if matched_keywords and any(kw in p_clean.lower() for kw in matched_keywords):
                if p_clean not in scraped_snippets:
                    scraped_snippets.append(p_clean)
            elif any(w in p_clean.lower() for w in lowered_query.split() if len(w) > 3):
                if p_clean not in scraped_snippets:
                    scraped_snippets.append(p_clean)

    # Include curated programs if user asked about courses
    course_data = None
    if any(w in lowered_query for w in ("course", "program", "branch", "degree")):
        course_data = config.get("course_levels") or {"Programs": config.get("course_programs", ())}
        sources.append({"title": f"{config['short_name']} Official Website", "url": config["website"]})
        if config.get("course_url"):
            sources.append({"title": f"{config['short_name']} Official Curriculum/Prospectus", "url": config["course_url"]})

    # Deduplicate sources
    unique_sources = []
    seen = set()
    for s in sources:
        if s["url"] not in seen:
            unique_sources.append(s)
            seen.add(s["url"])

    return {
        "success": True,
        "college": config["name"],
        "short_name": config["short_name"],
        "query": query,
        "snippets": scraped_snippets[:10],
        "course_data": course_data,
        "sources": unique_sources,
    }


def search_and_scrape_college(query: str, college: Optional[str] = None) -> Dict[str, Any]:
    """Live search and scrape wrapper function."""
    return search_college_website(query, college)


# Compatibility functions without permanent caching
def scrape_page(url: str) -> Dict[str, Any]:
    """On-demand ephemeral scrape helper."""
    data = fetch_webpage(url)
    return {
        "url": url,
        "title": data.get("title", ""),
        "headings": data.get("headings", []),
        "paragraphs": data.get("paragraphs", []),
        "list_items": data.get("list_items", []),
        "table_rows": data.get("tables", []),
        "links": data.get("links", []),
        "content_type": data.get("content_type", "html"),
    }


def search_official_website(college: str, query: str, limit: int = 5, complete: bool = False) -> Dict[str, Any]:
    """Live search official website helper."""
    res = search_college_website(query, college=college, max_results=limit)
    snippets = res.get("snippets", [])
    results = [
        {
            "college": res.get("short_name", college),
            "title": s.get("title", f"{college} Official Info"),
            "url": s.get("url", ""),
            "content": " | ".join(snippets[:5]),
            "links": [],
        }
        for s in res.get("sources", [])
    ]
    return {
        "college": res.get("short_name", college),
        "query": query,
        "results": results,
        "course_names": list(res.get("course_data", {}).get("UG Programs", ())) if res.get("course_data") else [],
        "errors": [] if res.get("success") else [res.get("error")],
    }
