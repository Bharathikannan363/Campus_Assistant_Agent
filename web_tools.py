"""Cached official-site scraping helpers used by the public campus tools."""

from functools import lru_cache
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


SUPPORTED_COLLEGES = {
    "CEG": {
        "name": "College of Engineering Guindy",
        "website": "https://ceg.annauniv.edu/",
        "fallback": "https://www.annauniv.edu/",
        "course_url": "https://www.annauniv.edu/pdf/CEG_UG_Fee_Structure.pdf",
        "course_programs": (
            "Information Technology (IT)",
            "Computer Science and Engineering (CSE)",
            "Electronics and Communication Engineering (ECE)",
        ),
    },
    "MIT": {
        "name": "Madras Institute of Technology",
        "website": "https://mitindia.edu/",
        "fallback": "https://www.annauniv.edu/",
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
    },
    "ACT": {
        "name": "Alagappa College of Technology",
        "website": "https://act.annauniv.edu/",
        "fallback": "https://www.annauniv.edu/",
        "course_url": "https://www.annauniv.edu/pdf/ACT_UG_Fee_Structure.pdf",
    },
    "SAP": {
        "name": "School of Architecture and Planning",
        "website": "https://sap.annauniv.edu/",
        "fallback": "https://www.annauniv.edu/",
        "course_url": "https://www.annauniv.edu/pdf/SAP_UG_PG_Fee_Structure.pdf",
    },
}

QUERY_KEYWORDS = {
    "departments": ("department", "departments", "faculty", "school", "branch"),
    "courses": ("course", "courses", "programme", "programmes", "program", "degree", "prospectus", "ug", "pg", "b.e", "b.tech", "m.e", "m.tech", "m.sc", "ph.d"),
    "admissions": ("admission", "admissions", "apply", "eligibility", "application", "fees", "counselling"),
    "facilities": ("facility", "facilities", "library", "hostel", "canteen", "laboratory", "lab", "sports", "auditorium", "gym"),
    "locations": ("location", "located", "campus", "building", "landmark", "map"),
    "announcements": ("announcement", "announcements", "news", "notice", "notices", "circular", "events"),
    "academic": ("academic", "calendar", "regulation", "curriculum", "syllabus", "semester", "examination"),
    "contacts": ("contact", "phone", "email", "address", "office", "dean"),
    "general": ("college", "campus", "about", "overview"),
}

IRRELEVANT_CONTENT_TERMS = (
    "alumni", "alumnus", "convocation", "chairman", "governor",
    "biography", "born in", "schooling", "doctoral studies",
    "commentator", "copyright", "syndicate",
)
COURSE_NOISE_TERMS = (
    "programme", "programmes", "course", "courses", "academic",
    "prospectus", "admission", "fee", "subject", "regulation",
    "calendar", "centre", "department", "notification",
)


def _college_config(college):
    key = str(college).upper().strip()
    if key not in SUPPORTED_COLLEGES:
        raise ValueError("Only CEG, MIT, ACT, and SAP are supported.")
    return key, SUPPORTED_COLLEGES[key]


@lru_cache(maxsize=64)
def scrape_page(url):
    response = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Campusly official-source reader)"},
        timeout=15,
    )
    response.raise_for_status()
    if "application/pdf" in response.headers.get("content-type", "").lower() or response.content[:4] == b"%PDF":
        return {
            "url": url, "title": "", "headings": [], "paragraphs": [],
            "list_items": [], "links": [], "content_type": "pdf",
        }
    soup = BeautifulSoup(response.text, "lxml")
    for node in soup(["script", "style", "noscript"]):
        node.decompose()
    links = []
    for anchor in soup.find_all("a", href=True):
        href = urljoin(url, anchor["href"]).split("#", 1)[0]
        if urlparse(href).scheme in ("http", "https"):
            links.append({
                "text": " ".join(anchor.get_text(" ", strip=True).split()),
                "url": href,
            })
    return {
        "url": url,
        "title": soup.title.get_text(" ", strip=True) if soup.title else "",
        "headings": [" ".join(node.get_text(" ", strip=True).split()) for node in soup.find_all(["h1", "h2", "h3", "h4"])],
        "paragraphs": [" ".join(node.get_text(" ", strip=True).split()) for node in soup.find_all("p")],
        "list_items": [" ".join(node.get_text(" ", strip=True).split()) for node in soup.find_all("li")],
        "links": links,
    }


def _page_text(page):
    return " ".join([page["title"], *page["headings"], *page["paragraphs"], *page["list_items"]])


def _relevant_content(page, terms, complete=False):
    candidates = page["headings"] + page["paragraphs"] + page["list_items"]
    matches = []
    for item in candidates:
        clean = " ".join(item.split())
        lowered = clean.lower()
        if (
            len(clean) > 320
            or "administration administrators syndicate" in lowered
            or any(term in lowered for term in IRRELEVANT_CONTENT_TERMS)
        ):
            continue
        if clean and any(term in lowered for term in terms):
            if clean not in matches:
                matches.append(clean)
    for link in page["links"]:
        label = " ".join(link["text"].split())
        haystack = f"{label} {link['url']}".lower()
        if label and any(term in haystack for term in terms):
            item = f"{label}: {link['url']}"
            if item not in matches:
                matches.append(item)
    return " | ".join(matches if complete else matches[:25])[:12000 if complete else 4500]


def _course_names(pages, college):
    names = []
    other_colleges = {
        "CEG": ("madras institute", "alaggapa", "alagappa", "school of architecture", "mit campus", "act campus", "sap campus"),
        "MIT": ("college of engineering guindy", "alaggapa", "alagappa", "school of architecture", "ceg campus", "act campus", "sap campus"),
        "ACT": ("college of engineering guindy", "madras institute", "school of architecture", "ceg campus", "mit campus", "sap campus"),
        "SAP": ("college of engineering guindy", "madras institute", "alaggapa", "alagappa", "ceg campus", "mit campus", "act campus"),
    }.get(college, ())
    for page in pages:
        for item in page["headings"] + page["list_items"]:
            clean = " ".join(item.split())
            lowered = clean.lower()
            if not clean or len(clean) > 120 or len(clean) < 5:
                continue
            if any(term in lowered for term in IRRELEVANT_CONTENT_TERMS + COURSE_NOISE_TERMS):
                continue
            if any(term in lowered for term in other_colleges):
                continue
            if any(term in lowered for term in ("board of", "computer society", "institute of", "institute for", "campus", "established in", "outlook", "petronas")):
                continue
            if not any(term in lowered for term in (
                "engineering", "technology", "science", "architecture",
                "planning", "design", "management", "computer", "chemical",
                "textile", "leather", "automobile", "aeronautical",
            )):
                continue
            if clean not in names:
                names.append(clean)
    return names


def search_official_website(college, query, limit=5, complete=False):
    key, config = _college_config(college)
    terms = set(str(query).lower().split())
    for category, keywords in QUERY_KEYWORDS.items():
        if terms.intersection(keywords):
            terms = set(keywords)
            break
    roots = [config["website"], config["fallback"]]
    pages = []
    visited = set()
    errors = []
    for root in roots:
        try:
            homepage = scrape_page(root)
        except requests.exceptions.Timeout:
            errors.append(f"{key} official website timed out")
            continue
        except requests.exceptions.RequestException as exc:
            errors.append(f"{key} official website could not be accessed: {exc}")
            continue
        pages.append(homepage)
        visited.add(homepage["url"])
        ranked_links = sorted(
            homepage["links"],
            key=lambda link: sum(term in (link["text"] + " " + link["url"]).lower() for term in terms),
            reverse=True,
        )
        link_budget = 60 if complete else 12
        queue = [(link, 1) for link in ranked_links[:link_budget]]
        processed = 0
        while queue and processed < (100 if complete else link_budget):
            link, depth = queue.pop(0)
            if link["url"] in visited or urlparse(link["url"]).netloc != urlparse(root).netloc:
                continue
            if not any(term in (link["text"] + " " + link["url"]).lower() for term in terms):
                continue
            try:
                child = scrape_page(link["url"])
                pages.append(child)
                visited.add(link["url"])
                processed += 1
                if complete and depth < 2:
                    child_links = sorted(
                        child["links"],
                        key=lambda item: sum(term in (item["text"] + " " + item["url"]).lower() for term in terms),
                        reverse=True,
                    )
                    queue.extend((item, depth + 1) for item in child_links[:30])
            except requests.exceptions.RequestException as exc:
                errors.append(f"{link['url']}: {exc}")
        if len(pages) > 1:
            break
    ranked_pages = sorted(
        pages,
        key=lambda page: sum(term in _page_text(page).lower() for term in terms),
        reverse=True,
    )
    results = []
    page_limit = len(ranked_pages) if complete else limit
    for page in ranked_pages[:page_limit]:
        text = _relevant_content(page, terms, complete=complete)
        if not text:
            continue
        results.append({
            "college": key,
            "title": page["title"] or page["url"],
            "url": page["url"],
            "content": text[:6000],
            "links": page["links"],
        })
    return {
        "college": key,
        "query": query,
        "results": results,
        "course_names": _course_names(pages, key) if "courses" in terms else [],
        "errors": errors,
    }
