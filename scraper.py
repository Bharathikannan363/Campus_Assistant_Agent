"""Robots-aware, college-specific scraping pipeline.

URLs are configuration, never fabricated. Disabled/empty definitions are
skipped and the pipeline records failures instead of bypassing site controls.
"""
import hashlib
from datetime import datetime, timezone
from urllib.parse import urlparse
from urllib import robotparser
import requests
from bs4 import BeautifulSoup
from database import get_connection

SCRAPER_CONFIG = {short: {"website": None, "pages": {}} for short in ("CEG", "MIT", "SAP", "ACT")}

def fetch_public_page(url, user_agent="AI-Campus-Assistant/1.0"):
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("Only valid public HTTP(S) URLs are allowed")
    robots = robotparser.RobotFileParser()
    robots.set_url(f"{parsed.scheme}://{parsed.netloc}/robots.txt")
    try: robots.read()
    except Exception: return None, "robots.txt could not be read; skipped for safety"
    if not robots.can_fetch(user_agent, url):
        return None, "robots.txt disallows this URL"
    try:
        response = requests.get(url, headers={"User-Agent": user_agent}, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        return None, str(exc)
    return BeautifulSoup(response.text, "html.parser").get_text(" ", strip=True), None

def scrape_college(college_id, short_name):
    config = SCRAPER_CONFIG.get(short_name, {})
    stats = {"college_id": college_id, "pages_scraped": 0, "records_added": 0, "errors": []}
    for page_type, url in config.get("pages", {}).items():
        if not url: continue
        content, error = fetch_public_page(url)
        digest = hashlib.sha256((content or "").encode()).hexdigest()
        db = get_connection()
        db.execute("INSERT INTO scraped_pages (college_id,url,page_type,content,content_hash,status,error_message) VALUES (?,?,?,?,?,?,?)",
                   (college_id, url, page_type, content, digest, "ok" if not error else "error", error))
        db.commit(); db.close()
        if error: stats["errors"].append(error)
        else: stats["pages_scraped"] += 1
    return stats
