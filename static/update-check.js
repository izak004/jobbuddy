(function () {
  const badge = document.getElementById("updateBadge");
  if (!badge) return;

  fetch("/api/check_update")
    .then(res => res.json())
    .then(data => {
      if (!data.checked) return; // offline or GitHub unreachable — leave the default "Up to date" showing
      if (data.update_available) {
        badge.textContent = "⬆ Update available";
        badge.title = `Installed: v${data.current} — Latest: v${data.latest}`;
        badge.href = data.repo_url;
        badge.target = "_blank";
        badge.classList.remove("badge-good");
        badge.classList.add("badge-warn");
        badge.style.cursor = "pointer";
      } else {
        badge.title = `Installed: v${data.current} (latest)`;
      }
    })
    .catch(() => { /* silently leave the default state — not worth surfacing an error for this */ });
})();
