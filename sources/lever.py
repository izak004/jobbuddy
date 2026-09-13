import requests
import json
import os
import settings
from .util import epoch_to_iso

COMPANIES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "companies.json")


def _load_tokens():
    with open(COMPANIES_PATH) as f:
        return json.load(f).get("lever", [])


def fetch():
    jobs = []
    relevant_terms = [t.lower() for t in settings.load()["interested_job_titles"]]
    for token in _load_tokens():
        try:
            resp = requests.get(
                f"https://api.lever.co/v0/postings/{token}", params={"mode": "json"}, timeout=20,
            )
            if resp.status_code != 200:
                continue
            data = resp.json()
        except Exception as e:
            print(f"[lever:{token}] fetch failed: {e}")
            continue

        for j in data:
            title = j.get("text", "") or ""
            desc = j.get("descriptionPlain", "") or j.get("description", "") or ""
            haystack = f"{title} {desc}".lower()
            if not any(term in haystack for term in relevant_terms):
                continue
            categories = j.get("categories", {}) or {}
            location = categories.get("location", "") or ""
            jobs.append({
                "source": f"lever:{token}",
                "source_id": j.get("id", ""),
                "title": title,
                "company": token,
                "location": location,
                "url": j.get("hostedUrl", ""),
                "description": desc,
                "posted_date": epoch_to_iso(j.get("createdAt"), unit="ms"),
                "remote_flag": (j.get("workplaceType") or "").lower() == "remote"
                or "remote" in location.lower(),
                "employment_type_raw": categories.get("commitment", ""),
            })
    return jobs
