import requests
import settings

API_URL = "https://remotive.com/api/remote-jobs"


def fetch():
    jobs = []
    seen_ids = set()
    search_terms = settings.load()["interested_job_titles"]
    for term in search_terms:
        try:
            resp = requests.get(API_URL, params={"search": term}, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[remotive] search '{term}' failed: {e}")
            continue
        for j in data.get("jobs", []):
            if j["id"] in seen_ids:
                continue
            seen_ids.add(j["id"])
            jobs.append({
                "source": "remotive",
                "source_id": str(j["id"]),
                "title": j.get("title", ""),
                "company": j.get("company_name", ""),
                "location": j.get("candidate_required_location", ""),
                "url": j.get("url", ""),
                "description": j.get("description", ""),
                "posted_date": j.get("publication_date", ""),
                "remote_flag": True,  # Remotive is remote-only by design
                "employment_type_raw": j.get("job_type", ""),
            })
    return jobs
