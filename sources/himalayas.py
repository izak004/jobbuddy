"""Himalayas — free public remote-jobs API, no key required.
https://himalayas.app/docs/remote-jobs-api

There's no server-side keyword search, and each page caps at ~20 results regardless of the
`limit` param, against a 100k+ job database — so a niche keyword needs several pages paged via
cursor to have a real chance of a hit, not just the most-recent 20 postings.
"""
import requests
import settings
from .util import epoch_to_iso

API_URL = "https://himalayas.app/jobs/api"
MAX_PAGES = 15


def fetch():
    jobs = []
    relevant_terms = [t.lower() for t in settings.load()["interested_job_titles"]]
    cursor = None

    for _ in range(MAX_PAGES):
        params = {"limit": 20}
        if cursor:
            params["cursor"] = cursor
        try:
            resp = requests.get(API_URL, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[himalayas] fetch failed: {e}")
            break

        for j in data.get("jobs", []):
            title = j.get("title", "") or ""
            description = j.get("description", "") or ""
            haystack = f"{title} {description}".lower()
            if not any(term in haystack for term in relevant_terms):
                continue

            restrictions = j.get("locationRestrictions") or []
            location = ", ".join(restrictions) if restrictions else "Anywhere"

            jobs.append({
                "source": "himalayas",
                "source_id": j.get("guid", ""),
                "title": title,
                "company": j.get("companyName", ""),
                "location": location,
                "url": j.get("applicationLink") or j.get("guid", ""),
                "description": description,
                "posted_date": epoch_to_iso(j.get("pubDate"), unit="s"),
                "remote_flag": True,  # Himalayas is remote-only by design
                "employment_type_raw": j.get("employmentType", ""),
            })

        cursor = data.get("nextCursor")
        if not cursor:
            break

    return jobs
