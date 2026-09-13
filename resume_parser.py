"""Best-effort generic .docx resume structure detection.

There's no reliable universal way to parse an arbitrary resume — this targets the common
convention most Word resumes already follow: bullet points use Word's bullet/numbered list
formatting, and each job entry has one or two plain (non-bulleted) lines above its bullets
(company name, then title/dates). If a resume doesn't follow that convention, detection will
be incomplete — that's why the setup wizard shows the detected structure for confirmation
before it's ever used, rather than trusting it silently.

Nothing detected here is ever edited except summary lines and job bullets — headings, company/
title/date lines, and any section after a recognized stop-heading (skills, education, etc.)
are only used to find boundaries, never modified.
"""
import re

SUMMARY_HEADING_WORDS = {"summary", "profile", "objective", "professional summary",
                          "career summary", "about me", "professional profile"}
EXPERIENCE_HEADING_WORDS = {"experience", "professional experience", "work experience",
                             "employment history", "employment", "career history",
                             "relevant experience"}
STOP_HEADING_WORDS = {"education", "skills", "technical skills", "core competencies",
                       "certifications", "certification", "computer skills", "quality skills",
                       "references", "projects", "publications", "awards", "languages",
                       "additional information", "volunteer", "training", "licenses"}

BULLET_CHARS = ("•", "-", "*", "‣", "●", "▪", "◦")


def _is_bullet_paragraph(p):
    style = (p.style.name or "").lower()
    if "list" in style or "bullet" in style:
        return True
    numPr = p._p.find(
        ".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}numPr"
    )
    if numPr is not None:
        return True
    text = p.text.strip()
    return bool(text) and text[0] in BULLET_CHARS


def _heading_kind(text):
    t = text.strip().lower().rstrip(":")
    if not t or len(t) > 50:
        return None
    if t in SUMMARY_HEADING_WORDS:
        return "summary"
    if t in EXPERIENCE_HEADING_WORDS:
        return "experience"
    if t in STOP_HEADING_WORDS:
        return "stop"
    return None


def parse_resume_structure(doc):
    paras = doc.paragraphs
    meta = []
    for i, p in enumerate(paras):
        text = p.text.strip()
        meta.append({
            "index": i,
            "text": text,
            "blank": not text,
            "bullet": _is_bullet_paragraph(p) if text else False,
            "heading": _heading_kind(text) if text and not _is_bullet_paragraph(p) else None,
        })

    warnings = []

    # --- Summary block ---
    summary_heading_idx = next((m["index"] for m in meta if m["heading"] == "summary"), None)
    if summary_heading_idx is not None:
        start = summary_heading_idx + 1
    else:
        start = 0
    summary_indices = []
    for m in meta[start:]:
        if m["heading"] is not None:
            break
        if not m["blank"]:
            summary_indices.append(m["index"])
    if not summary_indices:
        warnings.append("Couldn't find a summary section — nothing before the first heading, "
                         "or an explicit Summary/Profile heading with content under it.")

    # --- Experience section bounds ---
    exp_heading_idx = next((m["index"] for m in meta if m["heading"] == "experience"), None)
    if exp_heading_idx is None:
        warnings.append("Couldn't find a 'Professional Experience' / 'Work Experience' style "
                         "heading — only the summary will be available to tailor.")
        return {"summary_indices": summary_indices, "jobs": [], "warnings": warnings}

    exp_end = len(meta)
    for m in meta[exp_heading_idx + 1:]:
        if m["heading"] == "stop":
            exp_end = m["index"]
            break

    # --- Split experience section into job blocks ---
    jobs = []
    current = None
    in_bullets = False
    for m in meta[exp_heading_idx + 1: exp_end]:
        if m["blank"]:
            continue
        if m["bullet"]:
            if current is None:
                current = {"header_indices": [], "bullet_indices": []}
                jobs.append(current)
            current["bullet_indices"].append(m["index"])
            in_bullets = True
        else:
            if current is None or in_bullets:
                current = {"header_indices": [m["index"]], "bullet_indices": []}
                jobs.append(current)
                in_bullets = False
            else:
                current["header_indices"].append(m["index"])

    if not jobs:
        warnings.append("Found an experience section but no job entries in it — check that "
                         "your bullet points use Word's bullet-list formatting.")

    for j in jobs:
        j["label"] = " | ".join(paras[i].text.strip() for i in j["header_indices"]) or "(untitled role)"

    return {"summary_indices": summary_indices, "jobs": jobs, "warnings": warnings}
