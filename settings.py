"""User settings: the one file that separates 'this app' from 'this person's setup'.

Everything personal — API key, resume, job preferences, visa status — lives in
data/settings.json and data/resume.docx, both gitignored. The code in this repo never
contains anyone's real data; a fresh clone has neither file until the setup wizard runs.
"""
import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
SETTINGS_PATH = os.path.join(DATA_DIR, "settings.json")
RESUME_PATH = os.path.join(DATA_DIR, "resume.docx")

VISA_STATUS_CHOICES = {
    "citizen_or_pr": "US Citizen / Green Card / Permanent Resident",
    "independent_no_sponsorship": "Independent work authorization — no sponsorship needed (e.g. EAD, TN)",
    "needs_sponsorship": "I need an employer to sponsor my visa",
    "skip": "Skip visa-based filtering",
}

EMPLOYMENT_TYPE_CHOICES = {
    "full_time": "Full-time",
    "contract": "Contract",
    "part_time": "Part-time",
}

DEFAULTS = {
    "setup_completed": False,
    "full_name": "",
    "anthropic_api_key": "",
    "interested_job_titles": [],
    "excluded_job_titles": [],
    "remote_only": True,
    "target_country": "United States",
    "visa_status": "skip",
    "employment_types": ["full_time", "contract"],
    "max_posting_age_days": 14,
    "resume_structure": None,
    "adzuna_app_id": "",
    "adzuna_app_key": "",
}


def load():
    if not os.path.exists(SETTINGS_PATH):
        return dict(DEFAULTS)
    with open(SETTINGS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    merged = dict(DEFAULTS)
    merged.update(data)
    return merged


def save(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    current = load()
    current.update(data)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2)
    return current


def get_api_key():
    """The settings file is the primary store (what the UI writes to); an environment
    variable is honored too, e.g. for a user who prefers not to have the key on disk at all."""
    return load().get("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY") or ""


def is_configured():
    s = load()
    return bool(
        s.get("setup_completed")
        and get_api_key()
        and os.path.exists(RESUME_PATH)
        and s.get("interested_job_titles")
    )


def resume_exists():
    return os.path.exists(RESUME_PATH)
