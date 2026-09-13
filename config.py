"""Generic, non-personal defaults. Anything specific to one person (job titles, visa status,
location, resume) lives in settings.py / data/settings.json instead — this file only holds
constants that make sense as shared defaults for anyone using the app.
"""

# Soft penalties applied to a title regardless of field — these don't hide a listing, just
# rank it lower, since a title being an internship/entry-level role is rarely what an
# experienced job seeker wants regardless of what they typed as their interested titles.
SENIORITY_ADJUST = {
    "intern": -20,
    "internship": -20,
    "entry level": -15,
    "new graduate": -15,
}

# Postings requiring citizenship or a security clearance are excluded for anyone who isn't a
# citizen/permanent resident, regardless of visa_status otherwise.
CITIZENSHIP_CLEARANCE_PHRASES = [
    "u.s. citizen",
    "us citizen",
    "united states citizen",
    "must be a citizen",
    "citizens only",
    "citizenship required",
    "security clearance",
    "must hold a green card",
    "green card holder required",
    "permanent resident required",
    "lawful permanent resident status required",
]

# Phrases about visa sponsorship. How these are treated depends on visa_status:
# - "needs_sponsorship": these become hard excludes (no sponsorship offered = dealbreaker)
# - "independent_no_sponsorship": these are informational only (doesn't need sponsorship anyway)
# - "citizen_or_pr" / "skip": not checked at all
SPONSORSHIP_MENTION_PHRASES = [
    "sponsorship",
    "visa sponsorship",
    "sponsor a visa",
    "work authorization",
    "employment authorization",
]

# Aliases used to recognize a location string as being in a given target country. Extend
# freely — unrecognized target countries fall back to matching the raw country name string.
COUNTRY_ALIASES = {
    "united states": ["usa", "u.s.", "us", "united states", "america"],
    "united kingdom": ["uk", "united kingdom", "great britain", "england", "scotland", "wales"],
    "canada": ["canada"],
    "australia": ["australia"],
    "new zealand": ["new zealand"],
    "ireland": ["ireland"],
    "india": ["india"],
    "germany": ["germany"],
    "france": ["france"],
    "spain": ["spain"],
    "netherlands": ["netherlands"],
    "singapore": ["singapore"],
    "philippines": ["philippines"],
}

# Counts as "home" for any target country — a listing open to remote work from anywhere.
UNIVERSAL_REMOTE_HINTS = ["anywhere", "worldwide", "global"]

# Full set of country alias lists, used to detect a listing that's remote-but-tied-to-a-
# different-country (a hard miss for anyone restricted to working in their target country).
ALL_KNOWN_COUNTRIES = list(COUNTRY_ALIASES.keys())

# Adzuna requires a country code in its endpoint URL. Falls back to "us" for anything unlisted.
ADZUNA_COUNTRY_CODES = {
    "united states": "us",
    "united kingdom": "gb",
    "canada": "ca",
    "australia": "au",
    "germany": "de",
    "france": "fr",
    "netherlands": "nl",
    "india": "in",
    "singapore": "sg",
}

# Minimum score to show by default. Relevance/eligibility is enforced by the hard excludes in
# scoring.py (each -1000) — a title-gate-passing job always gets a +20 baseline, so this
# threshold only needs to clear small soft penalties, not act as a second relevance filter.
DEFAULT_MIN_SCORE = 5
