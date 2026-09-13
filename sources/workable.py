"""Workable — public per-company job board widget API, no key required.
https://apply.workable.com/api/v1/widget/accounts/{token}

The endpoint/wrapper ({name, description, jobs}) is confirmed live; the per-job field names
below follow Workable's documented public-jobs schema. Written defensively (.get() throughout)
since no company with currently open Workable roles was available to verify field names against
live data — a schema mismatch degrades to missing fields rather than a crash.
"""
import requests
import settings
from .companies import load_companies

BASE_URL = "https://apply.workable.com/api/v1/widget/accounts/{token}"


def fetch():
    jobs = []
    relevant_terms = [t.lower() for t in settings.load()["interested_job_titles"]]

    for token in load_companies("workable"):
        try:
            resp = requests.get(BASE_URL.format(token=token), timeout=20)
            if resp.status_code != 200:
                continue
            data = resp.json()
        except Exception as e:
            print(f"[workable:{token}] fetch failed: {e}")
            continue

        company_name = data.get("name", token)
        for j in data.get("jobs", []):
            title = j.get("title", "") or j.get("full_title", "") or ""
            if not any(term in title.lower() for term in relevant_terms):
                continue

            loc = j.get("location") or {}
            location = ", ".join(filter(None, [loc.get("city"), loc.get("region"), loc.get("country")]))

            jobs.append({
                "source": f"workable:{token}",
                "source_id": j.get("shortcode", "") or j.get("id", ""),
                "title": title,
                "company": company_name,
                "location": location,
                "url": j.get("url") or j.get("application_url") or j.get("shortlink", ""),
                "description": "",  # widget endpoint doesn't return full description
                "posted_date": j.get("published_on", ""),
                "remote_flag": bool(loc.get("telecommuting")),
                "employment_type_raw": j.get("employment_type", ""),
            })
    return jobs
