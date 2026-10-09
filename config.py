"""Configuration management for AI Campus Assistant Agent.

Loads environment variables, validates startup requirements, and configures
logging securely without leaking API keys or secrets.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

# Load environment variables
load_dotenv(dotenv_path=ENV_FILE, override=False)

# Logging configuration
LOG_FILE = BASE_DIR / "campus_assistant.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("campus_assistant")


def get_api_key() -> str:
    """Retrieve and validate the OpenRouter API key."""
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    return key


def get_model() -> str:
    """Retrieve the configured LLM model."""
    return os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini").strip()


def get_search_provider() -> str:
    """Retrieve the search provider (default: duckduckgo)."""
    return os.getenv("SEARCH_PROVIDER", "duckduckgo").strip().lower()


def get_search_api_key() -> str:
    """Retrieve search API key if configured."""
    return os.getenv("SEARCH_API_KEY", "").strip()


def get_campus_timezone() -> str:
    """Retrieve configured campus timezone (default: Asia/Kolkata)."""
    return os.getenv("CAMPUS_TIMEZONE", "Asia/Kolkata").strip()


def get_default_student_id() -> int:
    """Retrieve default student ID for single-student sessions."""
    try:
        return int(os.getenv("DEFAULT_STUDENT_ID", "101"))
    except ValueError:
        return 101


def get_database_path() -> Path:
    """Retrieve path to SQLite database."""
    custom_path = os.getenv("DATABASE_PATH")
    if custom_path:
        return Path(custom_path).resolve()
    return BASE_DIR / "campus.db"


def validate_config() -> dict:
    """Validate core configuration parameters and return status summary."""
    api_key = get_api_key()
    key_valid = bool(api_key and api_key.startswith("sk-or-"))
    
    return {
        "api_key_configured": bool(api_key),
        "api_key_valid_format": key_valid,
        "model": get_model(),
        "search_provider": get_search_provider(),
        "database_exists": get_database_path().exists(),
        "timezone": get_campus_timezone(),
        "default_student_id": get_default_student_id(),
    }
