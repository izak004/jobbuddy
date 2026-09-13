"""We Work Remotely — free public RSS feed, no key required.
Titles are formatted "Company: Job Title"; location isn't a separate field, so it's pulled
from the "Headquarters: ..." line most listings include at the top of their description.
"""
import datetime
import re
import xml.etree.ElementTree as ET

import requests
import settings

FEED_URL = "https://weworkremotely.com/remote-jobs.rss"
HEADQUARTERS_RE = re.compile(r"headquarters:\s*([^<\n]+)", re.IGNORECASE)


def _split_title(raw_title):
    if ":" in raw_title:
        company, _, title = raw_title.partition(":")
        return company.strip(), title.strip()
    return "", raw_title.strip()


def _extract_location(description):
    m = HEADQUARTERS_RE.search(description or "")
    return m.group(1).strip().rstrip(".") if m else ""


def _parse_rfc822_date(value):
    try:
        dt = datetime.datetime.strptime(value, "%a, %d %b %Y %H:%M:%S %z")
        return dt.isoformat()
    except (ValueError, TypeError):
        return ""


def fetch():
    jobs = []
    try:
        resp = requests.get(FEED_URL, timeout=20)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
    except Exception as e:
        print(f"[weworkremotely] fetch failed: {e}")
        return jobs

    relevant_terms = [t.lower() for t in settings.load()["interested_job_titles"]]
    for item in root.iter("item"):
        raw_title = (item.findtext("title") or "").strip()
        description = item.findtext("description") or ""
        company, title = _split_title(raw_title)
        haystack = f"{title} {description}".lower()
        if not any(term in haystack for term in relevant_terms):
            continue

        jobs.append({
            "source": "weworkremotely",
            "source_id": item.findtext("guid", ""),
            "title": title,
            "company": company,
            "location": _extract_location(description),
            "url": item.findtext("link", ""),
            "description": description,
            "posted_date": _parse_rfc822_date(item.findtext("pubDate", "")),
            "remote_flag": True,  # We Work Remotely is remote-only by design
            "employment_type_raw": item.findtext("type", ""),
        })
    return jobs
