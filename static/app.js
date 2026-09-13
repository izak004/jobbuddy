const jobListEl = document.getElementById("jobList");
const statsEl = document.getElementById("stats");
const resultCountEl = document.getElementById("resultCount");
const searchInput = document.getElementById("searchInput");
const statusFilter = document.getElementById("statusFilter");
const ageFilter = document.getElementById("ageFilter");
const showExcluded = document.getElementById("showExcluded");
const refreshBtn = document.getElementById("refreshBtn");
const themeToggle = document.getElementById("themeToggle");
const toastEl = document.getElementById("toast");

let debounceTimer = null;

function toast(msg, ms = 3500) {
  toastEl.textContent = msg;
  toastEl.classList.add("show");
  setTimeout(() => toastEl.classList.remove("show"), ms);
}

function escapeHtml(s) {
  const d = document.createElement("div");
  d.textContent = s || "";
  return d.innerHTML;
}

function stripHtml(html) {
  const d = document.createElement("div");
  d.innerHTML = html || "";
  return d.textContent || "";
}

// ---------- Theme toggle ----------
const THEME_KEY = "jobtracker-theme";
function applyTheme(theme) {
  if (theme === "system") document.documentElement.removeAttribute("data-theme");
  else document.documentElement.setAttribute("data-theme", theme);
}
function cycleTheme() {
  const current = localStorage.getItem(THEME_KEY) || "system";
  const next = { system: "light", light: "dark", dark: "system" }[current];
  localStorage.setItem(THEME_KEY, next);
  applyTheme(next);
  themeToggle.textContent = { system: "◐", light: "☀", dark: "☾" }[next];
}
applyTheme(localStorage.getItem(THEME_KEY) || "system");
themeToggle.textContent = { system: "◐", light: "☀", dark: "☾" }[localStorage.getItem(THEME_KEY) || "system"];
themeToggle.addEventListener("click", cycleTheme);

async function loadStats() {
  const res = await fetch("/api/stats");
  const s = await res.json();
  const applied = s.by_status.applied || 0;
  const interviewing = s.by_status.interviewing || 0;
  statsEl.textContent = `${s.total} tracked · ${s.new_today} new today · ${applied} applied · ${interviewing} interviewing`;

  const sub = document.getElementById("welcomeSub");
  if (sub) {
    sub.textContent = s.new_today > 0
      ? `${s.new_today} new match${s.new_today === 1 ? "" : "es"} found today, ${s.total} total tracked.`
      : `${s.total} jobs tracked so far — hit "Refresh jobs" to check for new matches.`;
  }
}

async function loadWelcomeName() {
  try {
    const res = await fetch("/api/settings");
    const s = await res.json();
    const heading = document.getElementById("welcomeHeading");
    if (heading && s.full_name) {
      heading.textContent = `Welcome back, ${s.full_name.split(" ")[0]}!`;
    }
  } catch (e) { /* ignore */ }
}

function buildQuery() {
  const params = new URLSearchParams();
  if (searchInput.value.trim()) params.set("search", searchInput.value.trim());
  if (statusFilter.value) params.set("status", statusFilter.value);
  if (showExcluded.checked) params.set("show_excluded", "1");
  params.set("max_age_days", ageFilter.value);
  return params.toString();
}

const EMPLOYMENT_LABELS = { full_time: "Full-time", contract: "Contract", part_time: "Part-time" };

function jobCardHtml(job) {
  const desc = stripHtml(job.description).slice(0, 220);
  const posted = job.posted_date ? job.posted_date.slice(0, 10) : "";
  const badges = [];

  if (job.us_remote) {
    badges.push(`<span class="badge badge-good">Remote confirmed</span>`);
  } else if (job.remote_ok) {
    badges.push(`<span class="badge badge-warn">Remote — verify location</span>`);
  } else {
    badges.push(`<span class="badge badge-warn">Not confirmed remote</span>`);
  }

  if (job.visa_flag === "exclude") {
    badges.push(`<span class="badge badge-bad" title="${escapeHtml(job.visa_flag_reason || "")}">⚠ Work-auth mismatch</span>`);
  } else if (job.visa_flag === "info") {
    badges.push(`<span class="badge badge-info" title="${escapeHtml(job.visa_flag_reason || "")}">ℹ Sponsorship mentioned</span>`);
  }

  if (job.employment_type && job.employment_type !== "unknown") {
    badges.push(`<span class="badge badge-neutral">${escapeHtml(EMPLOYMENT_LABELS[job.employment_type] || job.employment_type)}</span>`);
  }

  badges.push(`<span class="badge badge-neutral">${escapeHtml(job.source)}</span>`);

  const statusOptions = ["new", "interested", "applied", "interviewing", "offer", "rejected", "archived"]
    .map(s => `<option value="${s}" ${s === job.status ? "selected" : ""}>${s}</option>`)
    .join("");

  const pct = Math.max(0, Math.min(100, Math.round(job.score)));

  return `
  <div class="job-card" data-id="${job.id}">
    <div class="job-top">
      <div class="score-ring" style="--pct:${pct}; --ring-color:var(${job.score >= 25 ? "--teal" : job.score >= 15 ? "--accent" : "--amber"})"><div class="score-ring-inner">${Math.round(job.score)}</div></div>
      <div style="flex:1; min-width:0;">
        <p class="job-title"><a href="${escapeHtml(job.url)}" target="_blank" rel="noopener">${escapeHtml(job.title)}</a></p>
        <div class="job-meta">${escapeHtml(job.company)} · ${escapeHtml(job.location || "location n/a")}${posted ? " · posted " + posted : ""}</div>
        <div class="badges">${badges.join("")}</div>
      </div>
      <div class="job-controls">
        <select class="select statusSelect">${statusOptions}</select>
      </div>
    </div>
    <p class="job-desc">${escapeHtml(desc)}${desc.length >= 220 ? "…" : ""}</p>
    <textarea class="notes-area" placeholder="Notes (why interested, contacts, follow-ups)…">${escapeHtml(job.notes || "")}</textarea>
    <div class="tailor-row">
      <button class="btn btn-teal btn-sm tailorBtn" type="button">Update resume according to this job role</button>
      <span class="tailor-result"></span>
    </div>
  </div>`;
}

async function loadJobs() {
  const qs = buildQuery();
  const res = await fetch("/api/jobs?" + qs);
  const jobs = await res.json();
  resultCountEl.textContent = `${jobs.length} result${jobs.length === 1 ? "" : "s"}`;

  if (jobs.length === 0) {
    jobListEl.innerHTML = `<div class="empty-state"><div class="empty-icon">◈</div>No jobs match these filters yet.<br>Try "Refresh jobs", or widen your filters.</div>`;
    return;
  }
  jobListEl.innerHTML = jobs.map(jobCardHtml).join("");

  jobListEl.querySelectorAll(".statusSelect").forEach(sel => {
    sel.addEventListener("change", async (e) => {
      const id = e.target.closest(".job-card").dataset.id;
      const status = e.target.value;
      const body = { status };
      if (status === "applied") body.applied_date = new Date().toISOString().slice(0, 10);
      await fetch(`/api/jobs/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      toast("Status updated");
      loadStats();
    });
  });

  jobListEl.querySelectorAll(".notes-area").forEach(area => {
    area.addEventListener("blur", async (e) => {
      const id = e.target.closest(".job-card").dataset.id;
      await fetch(`/api/jobs/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ notes: e.target.value }),
      });
    });
  });

  jobListEl.querySelectorAll(".tailorBtn").forEach(btn => {
    btn.addEventListener("click", async (e) => {
      const card = e.target.closest(".job-card");
      const id = card.dataset.id;
      const resultEl = card.querySelector(".tailor-result");
      btn.disabled = true;
      btn.textContent = "Tailoring… (~15-20s)";
      resultEl.textContent = "";
      try {
        const res = await fetch(`/api/jobs/${id}/tailor_resume`, { method: "POST" });
        const data = await res.json();
        if (data.ok) {
          resultEl.innerHTML = `<a href="${data.download_url}" target="_blank">Download tailored resume →</a>`;
          toast("Tailored resume ready");
        } else {
          resultEl.textContent = data.error || "Failed";
          toast("Failed: " + (data.error || "unknown error"));
        }
      } catch (err) {
        resultEl.textContent = "Request failed: " + err.message;
        toast("Request failed: " + err.message);
      } finally {
        btn.disabled = false;
        btn.textContent = "Update resume according to this job role";
      }
    });
  });
}

function scheduleReload() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(loadJobs, 250);
}

searchInput.addEventListener("input", scheduleReload);
statusFilter.addEventListener("change", loadJobs);
ageFilter.addEventListener("change", loadJobs);
showExcluded.addEventListener("change", loadJobs);

refreshBtn.addEventListener("click", async () => {
  refreshBtn.disabled = true;
  refreshBtn.textContent = "Refreshing… (~30s)";
  try {
    const res = await fetch("/api/refresh", { method: "POST" });
    const data = await res.json();
    toast(data.ok ? "Refresh complete" : "Refresh finished with errors — check console log");
    console.log(data.log);
  } catch (e) {
    toast("Refresh failed: " + e.message);
  } finally {
    refreshBtn.disabled = false;
    refreshBtn.textContent = "Refresh jobs";
    loadJobs();
    loadStats();
  }
});

loadJobs();
loadStats();
loadWelcomeName();
