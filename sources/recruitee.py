"""Recruitee — public per-company job board API, no key required.
https://{token}.recruitee.com/api/offers/ — has a direct `remote` boolean field.
"""
import datetime

import requests
import settings
from .companies import load_companies

BASE_URL = "https://{token}.recruitee.com/api/offers/"


def _parse_date(value):
    """Recruitee dates look like '2026-09-09 15:14:08 UTC' — not directly ISO-parseable."""
    if not value:
        return ""
    try:
        dt = datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S %Z")
        return dt.replace(tzinfo=datetime.timezone.utc).isoformat()
    except ValueError:
        return ""


def fetch():
    jobs = []
    relevant_terms = [t.lower() for t in settings.load()["interested_job_titles"]]

    for token in load_companies("recruitee"):
        try:
            resp = requests.get(BASE_URL.format(token=token), timeout=20)
            if resp.status_code != 200:
                continue
            data = resp.json()
        except Exception as e:
            print(f"[recruitee:{token}] fetch failed: {e}")
            continue

        for j in data.get("offers", []):
            title = j.get("title", "") or ""
            description = j.get("description", "") or ""
            haystack = f"{title} {description}".lower()
            if not any(term in haystack for term in relevant_terms):
                continue

            location = j.get("location") or j.get("country") or ""

            jobs.append({
                "source": f"recruitee:{token}",
                "source_id": str(j.get("id", "")),
                "title": title,
                "company": j.get("company_name", token),
                "location": location,
                "url": j.get("careers_url", ""),
                "description": description,
                "posted_date": _parse_date(j.get("published_at")) or _parse_date(j.get("created_at")),
                "remote_flag": bool(j.get("remote")),
                "employment_type_raw": j.get("employment_type_code", ""),
            })
    return jobs
