"""Working Nomads — free public remote-jobs API, no key required.
https://www.workingnomads.com/api/exposed_jobs/ — includes full descriptions and a location
field directly, unlike several other free sources.
"""
import requests
import settings

API_URL = "https://www.workingnomads.com/api/exposed_jobs/"


def fetch():
    jobs = []
    try:
        resp = requests.get(API_URL, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[workingnomads] fetch failed: {e}")
        return jobs

    relevant_terms = [t.lower() for t in settings.load()["interested_job_titles"]]
    for j in data:
        title = j.get("title", "") or ""
        description = j.get("description", "") or ""
        haystack = f"{title} {description}".lower()
        if not any(term in haystack for term in relevant_terms):
            continue

        jobs.append({
            "source": "workingnomads",
            "source_id": j.get("url", ""),
            "title": title,
            "company": j.get("company_name", ""),
            "location": j.get("location", "") or "Worldwide",
            "url": j.get("url", ""),
            "description": description,
            "posted_date": j.get("pub_date", ""),
            "remote_flag": True,  # Working Nomads is remote-only by design
        })
    return jobs
