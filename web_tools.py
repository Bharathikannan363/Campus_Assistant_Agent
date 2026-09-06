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
    },
    "MIT": {
        "name": "Madras Institute of Technology",
        "website": "https://mitindia.edu/",
        "fallback": "https://www.annauniv.edu/",
        "course_url": "https://www.annauniv.edu/pdf/MIT_UG_Fee_Structure.pdf",
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
    "announcements": ("announcement", "announcements", "news", "notice", "notices", "circular", "events"),
    "academic": ("academic", "calendar", "regulation", "curriculum", "syllabus", "semester", "examination"),
    "contacts": ("contact", "phone", "email", "address", "office", "dean"),
    "general": ("college", "campus", "about", "overview"),
}


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


def _relevant_content(page, terms):
    candidates = page["headings"] + page["list_items"]
    matches = []
    for item in candidates:
        clean = " ".join(item.split())
        lowered = clean.lower()
        if len(clean) > 180 or "administration administrators syndicate" in lowered:
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
    return " ".join(matches[:25])[:4500]


def search_official_website(college, query, limit=5):
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
        for link in ranked_links[:12]:
            if link["url"] in visited or urlparse(link["url"]).netloc != urlparse(root).netloc:
                continue
            if not any(term in (link["text"] + " " + link["url"]).lower() for term in terms):
                continue
            try:
                pages.append(scrape_page(link["url"]))
                visited.add(link["url"])
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
    for page in ranked_pages[:limit]:
        text = _relevant_content(page, terms)
        if not text:
            continue
        results.append({
            "college": key,
            "title": page["title"] or page["url"],
            "url": page["url"],
            "content": text[:6000],
            "links": page["links"],
        })
    return {"college": key, "query": query, "results": results, "errors": errors}
