"""Rule-based scoring: no LLM calls, runs fully offline/free. Driven by user settings
(interested/excluded titles, remote/country preference, visa status, employment type) rather
than any hardcoded field or identity — see settings.py for what's configurable."""
import json
import re

import config
import settings

EMPLOYMENT_TYPE_HINTS = {
    "contract": ["contract", "contractor", "temporary", "temp ", "fixed-term", "freelance"],
    "part_time": ["part-time", "part time"],
    "full_time": ["full-time", "full time", "permanent"],
}


def _matches_any(text, phrases):
    """Word-boundary-safe phrase matching. Naive substring checks would let 'us' match
    inside 'Austin' or 'india' match inside 'Indianapolis' — both real false positives
    seen during testing."""
    for phrase in phrases:
        phrase = phrase.strip().lower()
        if not phrase:
            continue
        pattern = r"\b" + re.escape(phrase) if "." in phrase else r"\b" + re.escape(phrase) + r"\b"
        if re.search(pattern, text):
            return True
    return False


def _text_for_matching(title, description):
    return f"{title}\n{description}".lower()


def score_keywords(title, description, interested_titles):
    """Baseline ranking signal: jobs whose description also repeats the user's interested-title
    phrases (not just the title itself) are more deeply on-topic, not just title-matched."""
    text = _text_for_matching(title, description)
    breakdown = {}
    total = 0
    for phrase in interested_titles:
        phrase = phrase.strip().lower()
        if phrase and phrase in text:
            breakdown[f"keyword:{phrase}"] = 8
            total += 8
    for phrase, delta in config.SENIORITY_ADJUST.items():
        if phrase in title.lower():
            breakdown[f"seniority:{phrase}"] = delta
            total += delta
    return total, breakdown


def detect_visa_flag(title, description, visa_status):
    if visa_status in ("citizen_or_pr", "skip"):
        return "ok", None
    text = _text_for_matching(title, description)
    for phrase in config.CITIZENSHIP_CLEARANCE_PHRASES:
        if phrase in text:
            return "exclude", f"Mentions '{phrase}' — not open to your work-authorization status."
    if visa_status == "needs_sponsorship":
        for phrase in config.SPONSORSHIP_MENTION_PHRASES:
            if phrase in text:
                return "exclude", f"Mentions '{phrase}' — you need sponsorship and this may not offer it."
        return "ok", None
    if visa_status == "independent_no_sponsorship":
        for phrase in config.SPONSORSHIP_MENTION_PHRASES:
            if phrase in text:
                return "info", f"Mentions '{phrase}' — your work authorization doesn't need sponsorship, so this is informational only."
    return "ok", None


def _country_hints(target_country):
    key = (target_country or "").strip().lower()
    aliases = config.COUNTRY_ALIASES.get(key, [key] if key else [])
    return aliases + config.UNIVERSAL_REMOTE_HINTS


def _other_country_hints(target_country):
    key = (target_country or "").strip().lower()
    hints = []
    for country, aliases in config.COUNTRY_ALIASES.items():
        if country != key:
            hints.extend(aliases)
    return hints


def detect_target_country_remote(location, remote_flag_from_source, target_country):
    """remote_ok comes from the source's own remote signal — never inferred from location text
    alone, since e.g. 'Austin, TX' is an onsite city, not a remote hint. Location text only
    decides in_target_country and confirmed_other_country, and only once remote_ok is true."""
    if not remote_flag_from_source:
        return False, False, False
    loc = (location or "").lower()
    if _matches_any(loc, _country_hints(target_country)):
        return True, True, False
    if _matches_any(loc, _other_country_hints(target_country)):
        return True, False, True
    return True, False, False


def detect_employment_type(title, description, structured_type=None):
    if structured_type:
        t = structured_type.strip().lower().replace(" ", "_").replace("-", "_")
        if "full" in t:
            return "full_time"
        if "contract" in t or "freelance" in t or "temp" in t:
            return "contract"
        if "part" in t:
            return "part_time"
    text = _text_for_matching(title, description)
    for etype, hints in EMPLOYMENT_TYPE_HINTS.items():
        if any(h in text for h in hints):
            return etype
    return "unknown"


def score_job(title, description, location, remote_flag_from_source, structured_employment_type=None):
    s = settings.load()
    interested_titles = s["interested_job_titles"]
    excluded_titles = s["excluded_job_titles"]
    remote_only = s["remote_only"]
    target_country = s["target_country"]
    visa_status = s["visa_status"]
    wanted_employment_types = set(s["employment_types"])

    kw_score, breakdown = score_keywords(title, description, interested_titles)
    visa_flag, visa_reason = detect_visa_flag(title, description, visa_status)
    remote_ok, in_target_country, confirmed_other_country = detect_target_country_remote(
        location, remote_flag_from_source, target_country
    )
    employment_type = detect_employment_type(title, description, structured_employment_type)

    score = kw_score
    if interested_titles and not _matches_any(title.lower(), interested_titles):
        score -= 1000
        breakdown["not_target_role_penalty"] = -1000
    else:
        # Confirmed on-topic by title alone — guarantee a solid baseline regardless of how
        # much description text a source provides (some sources are title/location-only).
        score += 20
        breakdown["target_role_bonus"] = 20

    if excluded_titles and _matches_any(title.lower(), excluded_titles):
        score -= 1000
        breakdown["excluded_title_penalty"] = -1000

    if remote_only:
        if not remote_ok:
            score -= 1000
            breakdown["not_remote_exclude_penalty"] = -1000
        elif confirmed_other_country:
            score -= 1000
            breakdown["other_country_exclude_penalty"] = -1000
        elif not in_target_country:
            score -= 10
            breakdown["remote_unconfirmed_country_penalty"] = -10

    if visa_flag == "exclude":
        score -= 1000
        breakdown["visa_exclude_penalty"] = -1000

    if employment_type != "unknown" and employment_type not in wanted_employment_types:
        score -= 1000
        breakdown["employment_type_exclude_penalty"] = -1000

    return {
        "score": score,
        "score_breakdown": json.dumps(breakdown),
        "visa_flag": visa_flag,
        "visa_flag_reason": visa_reason,
        "remote_ok": int(remote_ok),
        "us_remote": int(in_target_country),  # column name predates multi-country support
        "employment_type": employment_type,
    }
