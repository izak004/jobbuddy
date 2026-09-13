import requests
import json
import os
import settings

COMPANIES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "companies.json")


def _load_tokens():
    with open(COMPANIES_PATH) as f:
        return json.load(f).get("greenhouse", [])


def fetch():
    jobs = []
    relevant_terms = [t.lower() for t in settings.load()["interested_job_titles"]]
    for token in _load_tokens():
        try:
            resp = requests.get(
                f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs",
                params={"content": "true"}, timeout=20,
            )
            if resp.status_code != 200:
                continue
            data = resp.json()
        except Exception as e:
            print(f"[greenhouse:{token}] fetch failed: {e}")
            continue

        for j in data.get("jobs", []):
            title = j.get("title", "") or ""
            content = j.get("content", "") or ""
            haystack = f"{title} {content}".lower()
            if not any(term in haystack for term in relevant_terms):
                continue
            location = (j.get("location") or {}).get("name", "")
            jobs.append({
                "source": f"greenhouse:{token}",
                "source_id": str(j.get("id", "")),
                "title": title,
                "company": token,
                "location": location,
                "url": j.get("absolute_url", ""),
                "description": content,
                "posted_date": j.get("first_published") or j.get("updated_at", ""),
                "remote_flag": "remote" in location.lower(),
            })
    return jobs
