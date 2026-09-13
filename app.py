"""Local web dashboard for browsing/tracking remote job leads, tuned to your own settings.

Run with `python app.py`, then open http://127.0.0.1:5057
First run redirects to /setup until the required settings + resume are in place.
"""
import html
import os
import re
import subprocess
import sys

import docx
from flask import Flask, jsonify, request, render_template, send_from_directory, redirect

import config
import db
import resume_tailor
import settings
import update_check
from resume_parser import parse_resume_structure

app = Flask(__name__)
db.init_db()

SETUP_EXEMPT_PATHS = {"/setup", "/api/settings", "/api/resume/upload", "/api/resume/structure", "/api/check_update"}


@app.before_request
def _require_setup():
    if settings.is_configured():
        return None
    path = request.path
    if path in SETUP_EXEMPT_PATHS or path.startswith("/static/"):
        return None
    return redirect("/setup")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/setup")
def setup_page():
    return render_template("setup.html")


@app.route("/applied")
def applied_page():
    return render_template("applied.html")


@app.route("/api/applied")
def api_applied_jobs():
    return jsonify(db.list_applied_jobs())


@app.route("/api/settings")
def api_get_settings():
    s = settings.load()
    key = s.get("anthropic_api_key") or ""
    s["anthropic_api_key"] = ""  # never round-trip the real secret into the page
    s["has_api_key"] = bool(key or os.environ.get("ANTHROPIC_API_KEY"))
    s["api_key_display"] = f"••••{key[-4:]}" if key else ("(using environment variable)" if os.environ.get("ANTHROPIC_API_KEY") else "")
    s["resume_uploaded"] = settings.resume_exists()
    s["visa_status_choices"] = settings.VISA_STATUS_CHOICES
    s["employment_type_choices"] = settings.EMPLOYMENT_TYPE_CHOICES

    adzuna_key = s.get("adzuna_app_key") or ""
    s["has_adzuna"] = bool(s.get("adzuna_app_id") and adzuna_key)
    s["adzuna_app_key"] = ""  # never round-trip the real secret into the page
    s["adzuna_app_key_display"] = f"••••{adzuna_key[-4:]}" if adzuna_key else ""
    return jsonify(s)


@app.route("/api/settings", methods=["POST"])
def api_save_settings():
    data = request.get_json(force=True)
    update = {}
    for key in ("full_name", "target_country", "visa_status", "adzuna_app_id"):
        if key in data:
            update[key] = (data[key] or "").strip()
    for key in ("interested_job_titles", "excluded_job_titles", "employment_types"):
        if key in data:
            update[key] = [str(x).strip() for x in data[key] if str(x).strip()]
    if "remote_only" in data:
        update["remote_only"] = bool(data["remote_only"])
    if "max_posting_age_days" in data:
        update["max_posting_age_days"] = int(data["max_posting_age_days"])
    if data.get("anthropic_api_key"):
        update["anthropic_api_key"] = data["anthropic_api_key"].strip()
    if data.get("adzuna_app_key"):
        update["adzuna_app_key"] = data["adzuna_app_key"].strip()
    if data.get("mark_complete"):
        update["setup_completed"] = True
    saved = settings.save(update)
    saved["anthropic_api_key"] = ""
    saved["adzuna_app_key"] = ""
    return jsonify(saved)


@app.route("/api/resume/upload", methods=["POST"])
def api_upload_resume():
    file = request.files.get("resume")
    if not file or not file.filename:
        return jsonify({"error": "No file received"}), 400
    if not file.filename.lower().endswith(".docx"):
        return jsonify({"error": "Please upload a .docx file (legacy .doc and PDF aren't supported)"}), 400

    os.makedirs(settings.DATA_DIR, exist_ok=True)
    file.save(settings.RESUME_PATH)

    try:
        doc = docx.Document(settings.RESUME_PATH)
        structure = parse_resume_structure(doc)
    except Exception as e:
        return jsonify({"error": f"Couldn't read that file: {e}"}), 400

    settings.save({"resume_structure": structure})
    return jsonify({"ok": True, "structure": _structure_preview(structure)})


@app.route("/api/resume/structure")
def api_resume_structure():
    if not settings.resume_exists():
        return jsonify({"error": "No resume uploaded yet"}), 404
    structure = resume_tailor.get_or_parse_structure()
    return jsonify({"structure": _structure_preview(structure)})


def _structure_preview(structure):
    return {
        "summary_line_count": len(structure["summary_indices"]),
        "jobs": [{"label": j["label"], "bullet_count": len(j["bullet_indices"])} for j in structure["jobs"]],
        "warnings": structure["warnings"],
    }


@app.route("/api/jobs")
def api_list_jobs():
    status = request.args.get("status") or None
    source = request.args.get("source") or None
    search = request.args.get("search") or None
    min_score = request.args.get("min_score")
    min_score = float(min_score) if min_score not in (None, "") else config.DEFAULT_MIN_SCORE
    show_excluded = request.args.get("show_excluded") == "1"
    if show_excluded:
        min_score = -10000

    max_age_days = request.args.get("max_age_days")
    if max_age_days in (None, ""):
        max_age_days = settings.load()["max_posting_age_days"]
    elif max_age_days == "any" or show_excluded:
        max_age_days = None
    else:
        max_age_days = int(max_age_days)

    jobs = db.list_jobs(status=status, min_score=min_score, search=search, source=source, max_age_days=max_age_days)
    return jsonify(jobs)


@app.route("/api/jobs/<int:job_id>")
def api_get_job(job_id):
    job = db.get_job(job_id)
    if not job:
        return jsonify({"error": "not found"}), 404
    return jsonify(job)


@app.route("/api/jobs/<int:job_id>", methods=["PATCH"])
def api_update_job(job_id):
    data = request.get_json(force=True)
    db.update_job_tracking(
        job_id,
        status=data.get("status"),
        notes=data.get("notes"),
        applied_date=data.get("applied_date"),
    )
    return jsonify(db.get_job(job_id))


@app.route("/api/stats")
def api_stats():
    return jsonify(db.stats())


@app.route("/api/check_update")
def api_check_update():
    return jsonify(update_check.check_for_update())


def _clean_description(raw_html):
    text = re.sub(r"<[^>]+>", " ", raw_html or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


@app.route("/api/jobs/<int:job_id>/tailor_resume", methods=["POST"])
def api_tailor_resume(job_id):
    job = db.get_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    if not settings.get_api_key():
        return jsonify({"error": "No Anthropic API key configured. Add one in Settings."}), 400

    try:
        description = _clean_description(job.get("description", ""))
        filename = resume_tailor.tailor_resume_for_job(job["title"], job["company"], description)
    except (FileNotFoundError, ValueError) as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to tailor resume: {e}"}), 500

    db.set_tailored_resume(job_id, filename)
    return jsonify({"ok": True, "filename": filename, "download_url": f"/download_resume/{filename}"})


@app.route("/download_resume/<path:filename>")
def download_resume(filename):
    return send_from_directory(resume_tailor.OUTPUT_DIR, filename, as_attachment=True)


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    """Run the fetch pipeline synchronously and report how many new jobs were added."""
    proc = subprocess.run(
        [sys.executable, "fetch_jobs.py"], capture_output=True, text=True, cwd=".", timeout=180,
    )
    return jsonify({
        "ok": proc.returncode == 0,
        "log": proc.stdout[-4000:] + ("\n" + proc.stderr[-2000:] if proc.stderr else ""),
    })


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5057, debug=False, threaded=True)
