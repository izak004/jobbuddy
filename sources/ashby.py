"""Ashby — public per-company job board API, no key required.
https://api.ashbyhq.com/posting-api/job-board/{token} — richer than most: includes a direct
isRemote boolean and a structured addressCountry field, so no location-text guessing needed.
"""
import requests
import settings
from .companies import load_companies

BASE_URL = "https://api.ashbyhq.com/posting-api/job-board/{token}"


def fetch():
    jobs = []
    relevant_terms = [t.lower() for t in settings.load()["interested_job_titles"]]

    for token in load_companies("ashby"):
        try:
            resp = requests.get(BASE_URL.format(token=token), timeout=20)
            if resp.status_code != 200:
                continue
            data = resp.json()
        except Exception as e:
            print(f"[ashby:{token}] fetch failed: {e}")
            continue

        for j in data.get("jobs", []):
            title = j.get("title", "") or ""
            description = j.get("descriptionPlain", "") or ""
            haystack = f"{title} {description}".lower()
            if not any(term in haystack for term in relevant_terms):
                continue

            location = j.get("location", "") or ""
            country = (j.get("address") or {}).get("postalAddress", {}).get("addressCountry", "")

            jobs.append({
                "source": f"ashby:{token}",
                "source_id": j.get("id", ""),
                "title": title,
                "company": token,
                "location": country or location,
                "url": j.get("jobUrl") or j.get("applyUrl", ""),
                "description": description,
                "posted_date": j.get("publishedAt", ""),
                "remote_flag": bool(j.get("isRemote")),
                "employment_type_raw": j.get("employmentType", ""),
            })
    return jobs
