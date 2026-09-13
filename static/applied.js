function escapeHtml(s) {
  const d = document.createElement("div");
  d.textContent = s || "";
  return d.innerHTML;
}

async function loadApplied() {
  const res = await fetch("/api/applied");
  const jobs = await res.json();
  const tbody = document.getElementById("appliedBody");
  const empty = document.getElementById("appliedEmpty");
  const table = document.getElementById("appliedTable");

  if (!jobs.length) {
    table.style.display = "none";
    empty.style.display = "block";
    return;
  }

  tbody.innerHTML = jobs.map((job, i) => {
    const dateApplied = job.applied_date || "—";
    const resumeCell = job.tailored_resume_filename
      ? `<a class="resume-link" href="/download_resume/${encodeURIComponent(job.tailored_resume_filename)}" target="_blank">${escapeHtml(job.tailored_resume_filename)}</a>`
      : `<span class="resume-none">Original resume</span>`;

    return `
      <tr>
        <td class="col-num">${i + 1}</td>
        <td><a class="job-link" href="${escapeHtml(job.url)}" target="_blank" rel="noopener">${escapeHtml(job.title)}</a></td>
        <td class="company-cell">${escapeHtml(job.company)}</td>
        <td class="date-cell">${escapeHtml(dateApplied)}</td>
        <td>${resumeCell}</td>
      </tr>`;
  }).join("");
}

loadApplied();
