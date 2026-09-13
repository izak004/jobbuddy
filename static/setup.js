const toastEl = document.getElementById("toast");
function toast(msg, ms = 3500) {
  toastEl.textContent = msg;
  toastEl.classList.add("show");
  setTimeout(() => toastEl.classList.remove("show"), ms);
}

// ---------- Tag input component ----------
function makeTagInput(container, initial, options = {}) {
  const tags = [...(initial || [])];
  const input = document.createElement("input");
  input.type = "text";
  input.placeholder = container.dataset.placeholder || "";

  function render() {
    container.innerHTML = "";
    tags.forEach((tag, i) => {
      const chip = document.createElement("span");
      chip.className = "tag-chip" + (options.variant === "excluded" ? " excluded" : "");
      chip.innerHTML = `${escapeHtml(tag)} <button type="button" aria-label="Remove">×</button>`;
      chip.querySelector("button").addEventListener("click", () => {
        tags.splice(i, 1);
        render();
      });
      container.appendChild(chip);
    });
    container.appendChild(input);
  }

  function commit() {
    const v = input.value.trim();
    if (v && !tags.includes(v)) {
      tags.push(v);
      input.value = "";
      render();
    } else {
      input.value = "";
    }
  }

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === ",") { e.preventDefault(); commit(); }
    if (e.key === "Backspace" && !input.value && tags.length) {
      tags.pop();
      render();
    }
  });
  input.addEventListener("blur", commit);
  container.addEventListener("click", () => input.focus());

  render();
  return { getTags: () => tags.slice() };
}

function escapeHtml(s) {
  const d = document.createElement("div");
  d.textContent = s || "";
  return d.innerHTML;
}

// ---------- State ----------
let interestedTagsCtl, excludedTagsCtl;
let selectedVisa = "skip";
let selectedEmploymentTypes = new Set(["full_time", "contract"]);
let hasStoredKey = false;

const VISA_DESCRIPTIONS = {
  citizen_or_pr: "No visa-related filtering applied — you're eligible for everything else on the merits.",
  independent_no_sponsorship: "Postings that mention sponsorship are shown as informational only, not excluded — you don't need it.",
  needs_sponsorship: "Postings that say sponsorship isn't offered are excluded, since that would be a dealbreaker for you.",
  skip: "No visa-based filtering at all — postings requiring citizenship still show up.",
};

async function loadSettings() {
  const res = await fetch("/api/settings");
  const s = await res.json();

  document.getElementById("fullNameInput").value = s.full_name || "";
  document.getElementById("remoteOnlyToggle").checked = !!s.remote_only;
  document.getElementById("targetCountryInput").value = s.target_country || "";
  document.getElementById("maxAgeSelect").value = String(s.max_posting_age_days || 14);

  hasStoredKey = s.has_api_key;
  document.getElementById("apiKeyStatus").textContent = hasStoredKey
    ? `Current key: ${s.api_key_display}. Leave blank to keep it.`
    : "No key set yet.";

  document.getElementById("adzunaAppId").value = s.adzuna_app_id || "";
  document.getElementById("adzunaAppKey").placeholder = s.has_adzuna
    ? `App Key (current: ${s.adzuna_app_key_display}, leave blank to keep it)`
    : "App Key";

  interestedTagsCtl = makeTagInput(document.getElementById("interestedTags"), s.interested_job_titles);
  excludedTagsCtl = makeTagInput(document.getElementById("excludedTags"), s.excluded_job_titles, { variant: "excluded" });

  selectedVisa = s.visa_status || "skip";
  renderVisaChoices(s.visa_status_choices);

  selectedEmploymentTypes = new Set(s.employment_types || []);
  renderEmploymentChips(s.employment_type_choices);

  if (s.resume_uploaded) {
    document.getElementById("resumeCurrentRow").style.display = "flex";
    loadStructurePreview();
  }

  if (s.setup_completed) {
    document.getElementById("backLink").style.display = "inline-flex";
    document.getElementById("saveBtn").textContent = "Save changes";
  }

  updateNavDots(s);
}

function renderVisaChoices(choices) {
  const el = document.getElementById("visaChoices");
  el.innerHTML = "";
  Object.entries(choices).forEach(([key, label]) => {
    const card = document.createElement("label");
    card.className = "choice-card" + (key === selectedVisa ? " selected" : "");
    card.innerHTML = `
      <input type="radio" name="visa" value="${key}" ${key === selectedVisa ? "checked" : ""}>
      <div>
        <div class="choice-title">${escapeHtml(label)}</div>
        <div class="choice-desc">${escapeHtml(VISA_DESCRIPTIONS[key] || "")}</div>
      </div>`;
    card.querySelector("input").addEventListener("change", () => {
      selectedVisa = key;
      el.querySelectorAll(".choice-card").forEach(c => c.classList.remove("selected"));
      card.classList.add("selected");
    });
    el.appendChild(card);
  });
}

function renderEmploymentChips(choices) {
  const el = document.getElementById("employmentTypeChips");
  el.innerHTML = "";
  Object.entries(choices).forEach(([key, label]) => {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "chip-toggle" + (selectedEmploymentTypes.has(key) ? " active" : "");
    chip.textContent = label;
    chip.addEventListener("click", () => {
      if (selectedEmploymentTypes.has(key)) selectedEmploymentTypes.delete(key);
      else selectedEmploymentTypes.add(key);
      chip.classList.toggle("active");
    });
    el.appendChild(chip);
  });
}

function renderStructurePreview(structure) {
  const el = document.getElementById("structurePreview");
  el.style.display = "block";
  let html = `<div class="structure-preview-title">Detected structure</div>`;
  html += `<div class="structure-row"><span>Summary</span><span>${structure.summary_line_count} line(s)</span></div>`;
  structure.jobs.forEach(j => {
    html += `<div class="structure-row"><span>${escapeHtml(j.label.slice(0, 50))}</span><span>${j.bullet_count} bullet(s)</span></div>`;
  });
  if (structure.warnings.length) {
    html += structure.warnings.map(w => `<div class="structure-warning">⚠ ${escapeHtml(w)}</div>`).join("");
  }
  el.innerHTML = html;
}

async function loadStructurePreview() {
  try {
    const res = await fetch("/api/resume/structure");
    if (!res.ok) return;
    const data = await res.json();
    renderStructurePreview(data.structure);
  } catch (e) { /* ignore */ }
}

function updateNavDots(s) {
  const checks = {
    api: hasStoredKey,
    resume: !!s.resume_uploaded,
    titles: (s.interested_job_titles || []).length > 0,
    location: !!s.target_country,
    type: (s.employment_types || []).length > 0,
  };
  Object.entries(checks).forEach(([key, done]) => {
    const item = document.querySelector(`.setup-nav-item[data-check="${key}"]`);
    if (item) item.classList.toggle("complete", done);
  });
}

// ---------- API key visibility ----------
const apiKeyInput = document.getElementById("apiKeyInput");
document.getElementById("toggleKeyVisibility").addEventListener("click", (e) => {
  const show = apiKeyInput.type === "password";
  apiKeyInput.type = show ? "text" : "password";
  e.target.textContent = show ? "Hide" : "Show";
});

// ---------- Resume upload ----------
const dropzone = document.getElementById("dropzone");
const resumeFile = document.getElementById("resumeFile");

dropzone.addEventListener("click", () => resumeFile.click());
dropzone.addEventListener("dragover", (e) => { e.preventDefault(); dropzone.classList.add("dragover"); });
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropzone.classList.remove("dragover");
  if (e.dataTransfer.files.length) uploadResume(e.dataTransfer.files[0]);
});
resumeFile.addEventListener("change", () => {
  if (resumeFile.files.length) uploadResume(resumeFile.files[0]);
});
document.getElementById("reparseBtn").addEventListener("click", loadStructurePreview);

async function uploadResume(file) {
  const fd = new FormData();
  fd.append("resume", file);
  toast("Uploading and analyzing resume…");
  try {
    const res = await fetch("/api/resume/upload", { method: "POST", body: fd });
    const data = await res.json();
    if (!res.ok) { toast("Error: " + data.error); return; }
    document.getElementById("resumeCurrentRow").style.display = "flex";
    renderStructurePreview(data.structure);
    document.querySelector('.setup-nav-item[data-check="resume"]').classList.add("complete");
    toast("Resume analyzed");
  } catch (e) {
    toast("Upload failed: " + e.message);
  }
}

// ---------- Save ----------
document.getElementById("saveBtn").addEventListener("click", async () => {
  const btn = document.getElementById("saveBtn");
  btn.disabled = true;
  const statusEl = document.getElementById("actionStatus");
  statusEl.textContent = "Saving…";

  const payload = {
    full_name: document.getElementById("fullNameInput").value,
    interested_job_titles: interestedTagsCtl.getTags(),
    excluded_job_titles: excludedTagsCtl.getTags(),
    remote_only: document.getElementById("remoteOnlyToggle").checked,
    target_country: document.getElementById("targetCountryInput").value,
    visa_status: selectedVisa,
    employment_types: [...selectedEmploymentTypes],
    max_posting_age_days: document.getElementById("maxAgeSelect").value,
    adzuna_app_id: document.getElementById("adzunaAppId").value,
    mark_complete: true,
  };
  if (apiKeyInput.value.trim()) payload.anthropic_api_key = apiKeyInput.value.trim();
  const adzunaKeyVal = document.getElementById("adzunaAppKey").value.trim();
  if (adzunaKeyVal) payload.adzuna_app_key = adzunaKeyVal;

  if (!payload.interested_job_titles.length) {
    statusEl.textContent = "Add at least one interested job title first.";
    btn.disabled = false;
    document.getElementById("sec-titles").scrollIntoView({ behavior: "smooth" });
    return;
  }

  try {
    await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    statusEl.textContent = "Saved — redirecting…";
    setTimeout(() => { window.location.href = "/"; }, 500);
  } catch (e) {
    statusEl.textContent = "Failed to save: " + e.message;
    btn.disabled = false;
  }
});

// ---------- Nav active-section highlight ----------
document.querySelectorAll(".setup-section").forEach(sec => {
  new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      // reserved for future active-state styling on scroll
    });
  }, { rootMargin: "-40% 0px -55% 0px" }).observe(sec);
});

loadSettings();
