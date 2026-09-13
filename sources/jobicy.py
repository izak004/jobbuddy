import requests
import settings

API_URL = "https://jobicy.com/api/v2/remote-jobs"


def fetch():
    jobs = []
    try:
        resp = requests.get(API_URL, params={"count": 100}, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[jobicy] fetch failed: {e}")
        return jobs

    relevant_terms = [t.lower() for t in settings.load()["interested_job_titles"]]
    for j in data.get("jobs", []):
        title = j.get("jobTitle", "") or ""
        excerpt = j.get("jobExcerpt", "") or ""
        haystack = f"{title} {excerpt}".lower()
        if not any(term in haystack for term in relevant_terms):
            continue
        job_type = ",".join(j.get("jobType") or [])
        jobs.append({
            "source": "jobicy",
            "source_id": str(j.get("id", j.get("jobSlug", ""))),
            "title": title,
            "company": j.get("companyName", ""),
            "location": j.get("jobGeo", ""),
            "url": j.get("url", ""),
            "description": j.get("jobDescription", excerpt),
            "posted_date": j.get("pubDate", ""),
            "remote_flag": True,  # Jobicy is remote-only by design
            "employment_type_raw": job_type,
        })
    return jobs
