"""Adzuna — general job aggregator, free tier requires a personal API key (instant signup at
developer.adzuna.com). Skipped silently if no key is configured. Free tier is capped around
100 queries/month, so this only runs one query per interested job title, not per page.
"""
import requests

import config
import settings

BASE_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/1"


def fetch():
    s = settings.load()
    app_id = s.get("adzuna_app_id")
    app_key = s.get("adzuna_app_key")
    if not app_id or not app_key:
        return []

    country_code = config.ADZUNA_COUNTRY_CODES.get(s["target_country"].strip().lower(), "us")
    url = BASE_URL.format(country=country_code)

    jobs = []
    seen_ids = set()
    for term in s["interested_job_titles"]:
        try:
            resp = requests.get(url, params={
                "app_id": app_id,
                "app_key": app_key,
                "what": term,
                "where": "remote",
                "results_per_page": 20,
                "content-type": "application/json",
            }, timeout=20)
            if resp.status_code == 401:
                print("[adzuna] 401 Unauthorized — check your app_id/app_key in Settings")
                return jobs
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[adzuna] search '{term}' failed: {e}")
            continue

        for j in data.get("results", []):
            job_id = str(j.get("id", ""))
            if job_id in seen_ids:
                continue
            seen_ids.add(job_id)

            location = (j.get("location") or {}).get("display_name", "")
            title = j.get("title", "") or ""
            description = j.get("description", "") or ""
            haystack = f"{title} {location} {description}".lower()

            jobs.append({
                "source": "adzuna",
                "source_id": job_id,
                "title": title,
                "company": (j.get("company") or {}).get("display_name", ""),
                "location": location,
                "url": j.get("redirect_url", ""),
                "description": description,
                "posted_date": j.get("created", ""),
                "remote_flag": "remote" in haystack,
                "employment_type_raw": j.get("contract_time", "") or j.get("contract_type", ""),
            })
    return jobs
