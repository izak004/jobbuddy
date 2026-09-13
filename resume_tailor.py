"""Generates a job-tailored copy of the user's resume using Claude.

Scope, by design: only the summary section and the bullet points under each job entry are
ever rewritten. Everything else — the document header (name/email/phone), company names, job
titles, dates, locations, and any section after a recognized stop-heading (skills, education,
etc.) — is structurally never touched; see resume_parser.py for how those boundaries are found.
"""
import datetime
import os
import re

import docx
from anthropic import Anthropic

import settings
from resume_parser import parse_resume_structure

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "tailored_resumes")
MODEL = "claude-sonnet-5"

TOOL_SCHEMA = {
    "name": "submit_tailored_resume",
    "description": "Submit the rewritten resume content, matching the exact item counts given.",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary_lines": {"type": "array", "items": {"type": "string"}},
            "jobs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"bullets": {"type": "array", "items": {"type": "string"}}},
                    "required": ["bullets"],
                },
            },
        },
        "required": ["summary_lines", "jobs"],
    },
}

SYSTEM_PROMPT = """You are helping a real job seeker tailor her existing, truthful resume to a \
specific job posting. Your only job is to reprioritize, rephrase, and re-emphasize her real, \
existing experience so a hiring manager can see the overlap with this specific role more easily.

Hard rules:
- Never invent facts: no new employers, job titles, dates, locations, degrees, certifications, \
tools, systems, or accomplishments beyond what is already present in the source text.
- Do not change or imply a different job title, company, date range, or location — those are not \
part of what you're given to edit, and are handled separately.
- Keep concrete, specific facts that are already present (named systems, named products, specific \
credentials, specific methodologies) — reword around them, don't strip them out or make them vaguer.
- Tone: grounded, specific, and modest. Do not inflate seniority, claim expert-level mastery, or \
use superlative language the original doesn't support. This should read as a natural, credible fit \
for the role, not an oversold one. It is fine to leave a line nearly unchanged if it's already \
relevant — you don't need to alter every single line.
- Match the existing resume's voice and length per line — short, dense, professional fragments, \
not full narrative sentences, similar length to the originals.
- You MUST return exactly the same number of summary lines and, for each job, exactly the same \
number of bullets as given to you, in the same order (rewrite item N in place — don't reorder, \
merge, or split items).

Call the submit_tailored_resume tool with your result."""


def _build_user_prompt(job_title, company, job_description, summary_texts, jobs):
    job_sections = []
    for i, job in enumerate(jobs):
        bullets = "\n".join(f"{n+1}. {t}" for n, t in enumerate(job["texts"]))
        job_sections.append(
            f"Job {i+1} — {job['label']} ({len(job['texts'])} bullets):\n{bullets}"
        )

    summary_block = "\n".join(f"{i+1}. {t}" for i, t in enumerate(summary_texts))

    return f"""TARGET JOB
Title: {job_title}
Company: {company}
Description:
{job_description[:6000]}

---
CURRENT RESUME CONTENT TO REWRITE (edit only this; do not add or remove entries)

Summary ({len(summary_texts)} lines):
{summary_block}

{chr(10).join(job_sections)}
"""


def _call_claude(job_title, company, job_description, summary_texts, jobs):
    api_key = settings.get_api_key()
    if not api_key:
        raise RuntimeError("No Anthropic API key configured. Add one in Settings.")
    client = Anthropic(api_key=api_key)
    message = client.messages.create(
        model=MODEL,
        max_tokens=6000,
        system=SYSTEM_PROMPT,
        tools=[TOOL_SCHEMA],
        tool_choice={"type": "tool", "name": "submit_tailored_resume"},
        messages=[{"role": "user", "content": _build_user_prompt(
            job_title, company, job_description, summary_texts, jobs)}],
    )
    for block in message.content:
        if block.type == "tool_use":
            return block.input
    raise RuntimeError("Claude did not return a tool_use block")


def _validate_counts(result, summary_texts, jobs):
    if len(result.get("summary_lines", [])) != len(summary_texts):
        return False, "summary"
    result_jobs = result.get("jobs", [])
    if len(result_jobs) != len(jobs):
        return False, "job count"
    for i, job in enumerate(jobs):
        if len(result_jobs[i].get("bullets", [])) != len(job["texts"]):
            return False, f"job {i+1} bullet count"
    return True, None


def _replace_paragraph_text(paragraph, new_text):
    """Swap only the run TEXT, preserving formatting — never restructure the paragraph.
    Leading whitespace-only runs (Word sometimes has a stray leading formatting run) are left
    untouched; only the runs from the first non-whitespace run onward are replaced."""
    runs = paragraph.runs
    if not runs:
        paragraph.add_run(new_text)
        return

    content_start = 0
    for i, r in enumerate(runs):
        if r.text.strip():
            content_start = i
            break

    template = runs[content_start]
    bold, italic, underline = template.bold, template.italic, template.underline
    font_name, font_size = template.font.name, template.font.size
    color = None
    if template.font.color and template.font.color.type is not None:
        color = template.font.color.rgb

    for r in list(runs[content_start:]):
        r._element.getparent().remove(r._element)

    new_run = paragraph.add_run(new_text)
    new_run.bold, new_run.italic, new_run.underline = bold, italic, underline
    if font_name:
        new_run.font.name = font_name
    if font_size:
        new_run.font.size = font_size
    if color:
        new_run.font.color.rgb = color


def _sanitize_filename(text):
    text = re.sub(r'[<>:"/\\|?*]', "", text)
    return re.sub(r"\s+", " ", text).strip()


def get_or_parse_structure(doc=None):
    """Returns the cached resume_structure from settings if present, else parses fresh
    (and caches it). Pass an already-open Document to avoid reopening the file twice."""
    s = settings.load()
    if s.get("resume_structure"):
        return s["resume_structure"]
    if doc is None:
        doc = docx.Document(settings.RESUME_PATH)
    structure = parse_resume_structure(doc)
    settings.save({"resume_structure": structure})
    return structure


def tailor_resume_for_job(job_title, company, job_description):
    if not settings.resume_exists():
        raise FileNotFoundError("No resume uploaded yet. Add one in Settings.")

    doc = docx.Document(settings.RESUME_PATH)
    structure = get_or_parse_structure(doc)

    summary_texts = [doc.paragraphs[i].text.strip() for i in structure["summary_indices"]]
    jobs = [
        {"label": j["label"], "bullet_indices": j["bullet_indices"],
         "texts": [doc.paragraphs[i].text.strip() for i in j["bullet_indices"]]}
        for j in structure["jobs"] if j["bullet_indices"]
    ]

    if not summary_texts and not jobs:
        raise ValueError("Nothing detected to tailor — the resume structure preview in Settings "
                          "couldn't find a summary or any job bullets.")

    result = _call_claude(job_title, company, job_description, summary_texts, jobs)
    ok, bad_part = _validate_counts(result, summary_texts, jobs)
    if not ok:
        result = _call_claude(
            job_title, company,
            job_description + f"\n\n(Your previous attempt returned the wrong number of items "
                               f"for '{bad_part}'. Match the exact counts given.)",
            summary_texts, jobs,
        )
        ok, bad_part = _validate_counts(result, summary_texts, jobs)
        if not ok:
            raise ValueError(f"Claude returned a mismatched item count for '{bad_part}' twice — aborting.")

    for i, idx in enumerate(structure["summary_indices"]):
        _replace_paragraph_text(doc.paragraphs[idx], result["summary_lines"][i])
    for job, result_job in zip(jobs, result["jobs"]):
        for i, idx in enumerate(job["bullet_indices"]):
            _replace_paragraph_text(doc.paragraphs[idx], result_job["bullets"][i])

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    name = settings.load().get("full_name") or "Resume"
    stamp = datetime.datetime.now().strftime("%Y%m%d")
    filename = _sanitize_filename(f"{name} - {company} - {job_title} - {stamp}.docx")
    output_path = os.path.join(OUTPUT_DIR, filename)
    doc.save(output_path)
    return filename
