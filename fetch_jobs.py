"""Daily job discovery run: pull from all sources, score, upsert into SQLite.

Run manually with `python fetch_jobs.py`, or schedule via Windows Task Scheduler
(see setup_task_scheduler.ps1 / README.md).
"""
import datetime
import sys

import db
import scoring
import settings
from sources import (
    remotive, jobicy, greenhouse, lever, simplyhired, himalayas, weworkremotely, adzuna,
    ashby, recruitee, workable, workday, workingnomads,
)

SOURCES = [
    remotive, jobicy, himalayas, weworkremotely, workingnomads, adzuna,
    greenhouse, lever, ashby, recruitee, workable, workday, simplyhired,
]


def run():
    if not settings.load()["interested_job_titles"]:
        print("No interested job titles configured yet — run setup first (open the dashboard, "
              "it'll redirect you). Skipping fetch.")
        return 0

    db.init_db()
    fetched_at = datetime.datetime.now().isoformat()
    total_seen, total_new = 0, 0

    for mod in SOURCES:
        name = mod.__name__.split(".")[-1]
        try:
            raw_jobs = mod.fetch()
        except Exception as e:
            print(f"[{name}] unhandled error: {e}")
            continue
        print(f"[{name}] fetched {len(raw_jobs)} candidate jobs")

        for rj in raw_jobs:
            if not rj.get("url") or not rj.get("title"):
                continue
            result = scoring.score_job(
                rj["title"], rj.get("description", ""), rj.get("location", ""),
                rj.get("remote_flag", False), rj.get("employment_type_raw"),
            )
            job = {
                **rj,
                **result,
                "fetched_at": fetched_at,
            }
            is_new = db.upsert_job(job)
            total_seen += 1
            total_new += int(is_new)

    print(f"Done. Seen {total_seen} jobs this run, {total_new} newly added.")
    return total_new


if __name__ == "__main__":
    sys.exit(0 if run() is not None else 1)
