"""Workday — powers career sites for many large enterprises (including much of big pharma:
Pfizer, Sanofi, AstraZeneca, MSD, and others). No public search-by-keyword-across-all-companies
exists; each company's Workday tenant is configured individually in companies.json, the same
pattern as Greenhouse/Lever, just with three parts (tenant/subdomain/site) instead of one token.

The CXS endpoint is public and unauthenticated: POST https://{tenant}.{subdomain}.myworkdayjobs.com
/wday/cxs/{tenant}/{site}/jobs — verified live against several real pharma company boards.
"""
import datetime
import re

import requests
import settings
from .companies import load_companies

RELATIVE_DATE_RE = re.compile(r"posted\s+(today|yesterday|(\d+)\+?\s*days?\s+ago)", re.IGNORECASE)


def _parse_posted_on(text):
    """Workday shows relative text like 'Posted Today', 'Posted 6 Days Ago', 'Posted 30+ Days
    Ago'. Converts to an approximate ISO date; unrecognized text is treated as fresh."""
    now = datetime.datetime.now(datetime.timezone.utc)
    m = RELATIVE_DATE_RE.search(text or "")
    if not m:
        return now.isoformat()
    if m.group(1).lower() == "today":
        return now.isoformat()
    if m.group(1).lower() == "yesterday":
        return (now - datetime.timedelta(days=1)).isoformat()
    days = int(m.group(2))
    return (now - datetime.timedelta(days=days)).isoformat()


def fetch():
    jobs = []
    relevant_terms = settings.load()["interested_job_titles"]

    for entry in load_companies("workday"):
        tenant, subdomain, site, display_name = (
            entry.get("tenant"), entry.get("subdomain"), entry.get("site"), entry.get("name", entry.get("tenant", ""))
        )
        if not (tenant and subdomain and site):
            continue
        base = f"https://{tenant}.{subdomain}.myworkdayjobs.com"
        endpoint = f"{base}/wday/cxs/{tenant}/{site}/jobs"

        for term in relevant_terms:
            try:
                resp = requests.post(
                    endpoint, json={"limit": 20, "offset": 0, "searchText": term}, timeout=20,
                )
                if resp.status_code != 200:
                    continue
                data = resp.json()
            except Exception as e:
                print(f"[workday:{tenant}] search '{term}' failed: {e}")
                continue

            for j in data.get("jobPostings", []):
                title = j.get("title", "") or ""
                location = j.get("locationsText", "") or ""
                external_path = j.get("externalPath", "")
                if not external_path:
                    continue
                url = f"{base}/{site}{external_path}"

                jobs.append({
                    "source": f"workday:{tenant}",
                    "source_id": url,
                    "title": title,
                    "company": display_name,
                    "location": location,
                    "url": url,
                    # Search results don't include the full description, only title/location —
                    # same limitation as SimplyHired; scores on title keywords only.
                    "description": "",
                    "posted_date": _parse_posted_on(j.get("postedOn", "")),
                    "remote_flag": "remote" in location.lower(),
                })
    return jobs
