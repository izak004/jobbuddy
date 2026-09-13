# JobBuddy

**A personal job-search assistant that runs entirely on your own laptop.** Tell it what you're
looking for once, and every day it quietly checks multiple job boards for you, filters out
everything that doesn't actually fit, and hands you a short list worth your time — plus a button
to generate a version of your resume tailored to any listing before you apply.

No cloud account, no subscription, no company harvesting your job search or your resume. It's a
Python + Flask app you run locally; the only outside call it ever makes on your behalf is to
Anthropic's API, and only at the exact moment you click "tailor resume" for a specific job.

## What to expect

- **A 5-minute first-time setup**: paste an API key, upload your resume, tell it what job titles
  you want (and don't want), your location/visa situation, and you're done — no config files to
  hand-edit.
- **A daily-refreshing dashboard**, not a one-time search: run it once and every future launch
  (or a scheduled background task) pulls in whatever's new, scored and ranked against your
  criteria, with a clear reason shown whenever something got filtered out.
- **Hard filters, not vibes**: a listing only appears if it actually matches your job titles, is
  genuinely remote (or matches wherever you said you're based), fits your visa/work-authorization
  situation, and isn't the seniority level you excluded. No sifting through noise.
- **One-click tailored resumes**: pick a listing, click a button, and get a `.docx` back with your
  summary and bullet points reworded to emphasize what's actually relevant to that job — never
  fabricated, never touching your name/dates/employers. Costs a few cents per resume, billed to
  your own API key.
- **A running record of what you've applied to** — company, date, which resume version you used —
  so three months from now you're not trying to remember.
- **Nothing about you lives in this repository.** Every install starts from zero; your resume, API
  key, and preferences are created locally the first time *you* run it, on your machine only.

## Quick start (Windows)

**Don't have Python or any dev tools installed?**
1. Click **Code → Download ZIP** above (or `git clone` this repo) and unzip it.
2. Double-click **`SETUP.bat`**.
3. It installs Python if needed, sets up an isolated environment, installs everything required,
   and opens the app in your browser automatically. One time only — takes a few minutes.

**Already have Python 3.10+?**
```powershell
git clone https://github.com/izak004/jobbuddy.git
cd jobbuddy
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m playwright install chromium
.venv\Scripts\python app.py
```
Then open http://127.0.0.1:5057.

Either way, the first launch takes you straight to a short setup form: your Anthropic API key
(only needed for resume tailoring — job discovery itself is free), your resume (`.docx`), the job
titles you're interested in and not interested in, your location/remote/visa preferences, and
employment type. Revisit it anytime via the **Setup** button in the header.

> **Note:** this is currently built and tested for **Windows**. The Python code itself is
> cross-platform, but `SETUP.bat`/`start_dashboard.bat` and the scheduled-task script are
> Windows-specific — macOS/Linux would need the manual `python`/`pip` steps above and your own
> equivalent of a launch script.

Inspired by the [career-ops](https://github.com/career-ops-hq/career-ops) philosophy ("a filter,
not spray-and-pray") but self-contained: no AI CLI subscription required, no external service
needed for the core job-discovery loop, and it never auto-applies anywhere — you always click
through and submit on the company's own site.

## Daily use

Double-click **`start_dashboard.bat`** (or open a terminal and run `app.py` directly) and go to
http://127.0.0.1:5057. Click **"Refresh jobs"** to pull the latest postings on demand, or set up
the included scheduled task for a fully automatic daily pull:
```powershell
powershell -ExecutionPolicy Bypass -File setup_task_scheduler.ps1
```
This registers a Windows Scheduled Task that runs `fetch_jobs.py` at 8:00 AM daily, so fresh
listings are waiting when you open the dashboard. Logs go to `data\fetch_log.txt`.

## What it does

Every fetch pulls postings from:
- **Remotive**, **Jobicy**, **Himalayas**, **We Work Remotely**, **Working Nomads** — public
  remote-job aggregator APIs/feeds, no key required
- **SimplyHired** — scraped with a headless browser (Playwright), since it has no public API. In
  practice this is the richest single source. See "About the SimplyHired scraper" below.
- **Adzuna** (optional) — general job aggregator; needs your own free API key from
  developer.adzuna.com, entered in Setup. Skipped entirely if not configured. Free tier is capped
  around 100 queries/month, so it runs one query per interested job title, not per page.
- **Company career pages** (`sources/companies.json`) — specific companies checked directly, so
  their newest postings aren't missed waiting for an aggregator to pick them up. Supports six ATS
  platforms: **Greenhouse, Lever, Ashby, Recruitee, Workable**, and **Workday**. Workday in
  particular is what powers career sites for a lot of large enterprises (including much of big
  pharma) that don't show up on Greenhouse/Lever at all — five real pharma companies (Pfizer,
  Sanofi, AstraZeneca, MSD, ProPharma Group) are pre-configured as a starting example. Add your own
  by visiting a company's careers page and checking which platform it redirects to — see the
  comment at the top of `companies.json` for the exact URL patterns to look for.

**Monster, CareerBuilder, and FlexJobs are intentionally not included.** Monster and CareerBuilder
sit behind DataDome, an active anti-bot CAPTCHA service — getting past that requires evasion
techniques out of scope regardless of the ToS question. FlexJobs requires a paid subscription;
scraping it without one would mean bypassing their paywall rather than automating something
you're entitled to see.

A listing only ever shows up if it clears every one of these (each is a hard exclude, not a soft
penalty), all driven by what you entered in Setup:
- Title actually matches one of your interested job titles (not just mentioned somewhere in the JD)
- Title doesn't match one of your excluded titles
- Confirmed remote if you set "remote only," and not remote-tied-to-a-different-country than the
  one you're authorized to work in
- No citizenship/security-clearance requirement (unless you're a citizen/permanent resident, in
  which case this isn't checked)
- If you selected "I need sponsorship," not explicitly stated as unavailable
- Matches an employment type you're open to (full-time/contract/part-time), when detectable
- Posted within your chosen freshness window (adjustable in the dashboard's dropdown)

Among listings that clear all of that, a keyword score ranks the best matches to your stated
interests first.

Everything is stored in a local SQLite database (`data/jobs.db`) so your notes and application
status persist across days.

## Tailored resumes

Every job card has an **"Update resume according to this job role"** button. It sends your resume
and that job's description to Claude, which rewrites only the professional summary and the
bullet points under each employer to emphasize your genuinely relevant existing experience — see
"About resume tailoring" below for exactly what it does and doesn't touch, and the cost.

## Applied Jobs

The **Applied Jobs** page (linked in the header) is your full application history — every job
you've ever marked "Applied," regardless of how old the posting is, sorted by the date you
applied. Each row shows the job title (linked to the original posting), the company, the date,
and which resume version you used (or "Original resume" if you applied without tailoring one).

## Using the dashboard

- **Search box** filters by title/company/description.
- **Status dropdown** per job: New → Interested → Applied → Interviewing → Offer / Rejected →
  Archived. Setting a job to "Applied" auto-stamps today's date and it appears on Applied Jobs.
- **Notes** field per job — jot why you're interested, contact names, follow-up dates. Saves on blur.
- **"Posted within"** dropdown — 7/14/30 days or any time.
- **"Show hidden listings"** checkbox reveals everything that got hard-excluded, in case you want
  to double-check one yourself.
- **Theme toggle** (◐) cycles system/light/dark.
- Badges on each card: score, remote confidence, visa flag, employment type, and source.

## Setup fields explained

- **Anthropic API key** — only used for resume tailoring; stored in `data/settings.json`
  (gitignored) or read from an `ANTHROPIC_API_KEY` environment variable if you prefer not to have
  it on disk at all.
- **Resume** — uploaded as a `.docx`, stored at `data/resume.docx`. On upload, JobBuddy analyzes
  its structure (summary + bullets per job entry) and shows you what it detected before anything
  is ever rewritten. This works best with resumes where bullet points use Word's native
  bullet-list formatting and each job entry has a plain (non-bulleted) company/title/date line —
  if your resume doesn't follow that convention, the preview will show what's missing.
- **Interested / not-interested job titles** — these both gate which listings show up *and* become
  the search terms sent to job boards.
- **Remote only / target country** — controls the remote and country-matching logic.
- **Work authorization** — four options, each changing how visa-related language is treated:
  citizen/permanent resident (no visa filtering at all), independent authorization like EAD/TN
  (sponsorship-mention is informational only, not a penalty), needs sponsorship (postings that
  rule out sponsorship are excluded), or skip filtering entirely.
- **Employment type & freshness** — which employment types you're open to, and how many days back
  to show postings from.

## Tuning it further

- **`config.py`** — soft seniority penalties (intern/entry-level), citizenship/clearance phrase
  list, sponsorship-mention phrase list, and the country-alias table used for remote/location
  matching. Extend `COUNTRY_ALIASES` if your target country isn't already listed.
- **`sources/companies.json`** — add companies relevant to your field. Visit a company's careers
  page and check which platform it redirects to: `boards.greenhouse.io/<token>`,
  `jobs.lever.co/<token>`, `jobs.ashbyhq.com/<token>`, `<token>.recruitee.com`,
  `apply.workable.com/<token>` — add the token to the matching list. Workday needs three parts
  instead of one token: from a URL like `pfizer.wd1.myworkdayjobs.com/PfizerCareers`, that's
  `{"tenant": "pfizer", "subdomain": "wd1", "site": "PfizerCareers", "name": "Pfizer"}`. Bad or
  renamed entries are skipped silently.

## About the SimplyHired scraper

Unlike the other sources, SimplyHired has no public API — `sources/simplyhired.py` drives a real
headless Chromium browser to load its search results page and read the DOM directly. Worth
knowing:

- **It's reading page structure, not a stable contract.** If SimplyHired redesigns their site,
  this will silently return 0 results until the selectors are updated.
- **It runs against SimplyHired's Terms of Service** for automated access. Scoped deliberately
  narrow — one search per keyword term, once a day — not something to scale up.
- **No full job description is fetched** (title/company/location only) — opening each listing
  individually would multiply the load on their site well past personal use. These listings score
  on title keywords only; click through to read the full JD.
- **The site's own "remote" filter isn't fully trusted** — testing turned up plain onsite listings
  even with it applied, so the scraper re-derives the remote signal from each listing's own
  location text.

## About resume tailoring

`resume_tailor.py` edits your uploaded resume directly using Claude (`claude-sonnet-5`), guided by
`resume_parser.py`'s best-effort structure detection (see "Setup fields explained" above).

- **Never touched, ever:** anything in the document header (name, email, phone), company names,
  job titles held, locations, dates, and any section after a recognized heading like Skills or
  Education. Only two kinds of content are ever sent to Claude: the summary section, and the
  bullet points under each detected job entry.
- **Formatting is preserved** by swapping only the text inside existing formatting runs — bullet
  styling, fonts, and bold headers are never rebuilt.
- **Told explicitly not to fabricate or oversell** — the prompt instructs Claude to only
  reprioritize and reword your real, existing experience (never invent employers, tools, dates, or
  accomplishments not already in the source), keep concrete facts intact, and keep the tone modest
  rather than inflating seniority. It's also told it's fine to leave an already-relevant bullet
  nearly unchanged rather than rewriting everything for the sake of it.
- **Always read the result before submitting it anywhere.** Treat it as a strong first draft, not
  a final copy.
- **Cost:** roughly $0.03–$0.08 per tailored resume. Output lands in `data/tailored_resumes/`,
  named after your name, the company, and the job title.
- **Privacy:** your resume content and the job description are sent to Anthropic's API for that
  one request. Nothing else leaves your machine.

## Design choices worth knowing about

- **No auto-apply.** This tool finds, scores, and helps you prepare — you decide and click submit.
- **Job discovery and scoring have no LLM cost.** It's deterministic keyword matching driven by
  your settings — free to run daily forever. Resume tailoring is the one feature that calls an
  LLM, only when you click the button.
- **Remote/location detection is a heuristic** based on the location string each source provides.
  Always verify on the actual posting before assuming eligibility.
- **Visa-flag detection is a heuristic**, not legal advice. Use it to prioritize your reading time,
  not as a final filter.

## What never gets committed to version control

`.gitignore` excludes `data/` (settings, resume, job database, tailored resumes) and any `.docx`
in the project. A fresh clone has none of your information — the setup wizard is what creates it,
locally, on whichever machine runs it.
