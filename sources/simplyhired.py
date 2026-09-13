"""Scrapes SimplyHired search results with a headless browser (Playwright) — SimplyHired
has no public API. This is slower and more fragile than the API-based sources (breaks if
they redesign the page), and runs against their Terms of Service for automated access.
Used here for personal, low-volume (once/day) job search only — never at scale.

Requires: `playwright install chromium` once, in addition to `pip install -r requirements.txt`.
"""
import datetime
import re

import settings

BASE_URL = "https://www.simplyhired.com/search"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


def _parse_relative_date(text):
    """SimplyHired shows short relative stamps like '1d', '3d', '1mo', '30+d'. Converts to
    an ISO date; unrecognized/'just posted'-style text is treated as fresh (today)."""
    text = (text or "").strip().lower()
    now = datetime.datetime.now(datetime.timezone.utc)
    m = re.match(r"(\d+)\+?\s*(h|d|mo|y)", text)
    if not m:
        return now.isoformat()
    n, unit = int(m.group(1)), m.group(2)
    days = {"h": 0, "d": n, "mo": n * 30, "y": n * 365}.get(unit, n)
    return (now - datetime.timedelta(days=days)).isoformat()


def fetch():
    jobs = []
    seen_urls = set()
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[simplyhired] playwright not installed — skipping. "
              "Run: pip install playwright && playwright install chromium")
        return jobs

    s = settings.load()
    location_param = "remote" if s["remote_only"] else s["target_country"]

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=USER_AGENT)
            for term in s["interested_job_titles"]:
                url = f"{BASE_URL}?q={term.replace(' ', '+')}&l={location_param.replace(' ', '+')}"
                try:
                    page.goto(url, timeout=30000, wait_until="domcontentloaded")
                    page.wait_for_timeout(2500)
                except Exception as e:
                    print(f"[simplyhired] navigation failed for '{term}': {e}")
                    continue

                cards = page.query_selector_all('[data-testid="searchSerpJob"]')
                for card in cards:
                    title_el = card.query_selector('[data-testid="searchSerpJobTitle"] a')
                    if not title_el:
                        continue
                    href = title_el.get_attribute("href") or ""
                    if not href:
                        continue
                    full_url = href if href.startswith("http") else f"https://www.simplyhired.com{href}"
                    if full_url in seen_urls:
                        continue
                    seen_urls.add(full_url)

                    company_el = card.query_selector('[data-testid="companyName"]')
                    location_el = card.query_selector('[data-testid="searchSerpJobLocation"]')
                    date_el = card.query_selector('[data-testid="searchSerpJobDateStamp"]')
                    location_text = (location_el.inner_text() if location_el else "").strip()

                    jobs.append({
                        "source": "simplyhired",
                        "source_id": full_url,
                        "title": (title_el.inner_text() or "").strip(),
                        "company": (company_el.inner_text() if company_el else "").strip(),
                        "location": location_text,
                        "url": full_url,
                        # Full JD requires opening each listing individually — too much
                        # extra load for a scraper already pushing its welcome. Title +
                        # location is enough to gate/score/link through; you read the rest
                        # on the actual posting.
                        "description": "",
                        "posted_date": _parse_relative_date(date_el.inner_text() if date_el else ""),
                        # Don't trust the site's own remote filter — it still surfaced at
                        # least one plain onsite listing during testing. Derive it from the
                        # listing's own location text instead, same as the other sources.
                        "remote_flag": "remote" in location_text.lower(),
                    })
            browser.close()
    except Exception as e:
        print(f"[simplyhired] unhandled error: {e}")
    return jobs
