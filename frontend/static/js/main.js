/**
 * Shared API helper — automatically attaches JWT and throws on error.
 */
async function api(url, method = "GET", body = null) {
  const headers = { "Content-Type": "application/json" };
  const token = localStorage.getItem("token");
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(url, {
    method,
    headers,
    body: body ? JSON.stringify(body) : null,
  });

  if (res.status === 401) {
    localStorage.clear();
    window.location.href = "/login";
    return;
  }

  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Something went wrong");
  return data;
}

/** Prevent XSS when injecting user content into innerHTML. */
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** Format an ISO date string into something readable. */
function formatDate(iso) {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

/**
 * Exercise library cache — fetched once per page load.
 * Returns an array of {id, name, category} objects.
 */
let _libraryCache = null;
async function getLibrary() {
  if (!_libraryCache) {
    _libraryCache = await api("/api/library/");
  }
  return _libraryCache;
}

// ── Unit helpers (lb / kg) ────────────────────────────────────────────────────

/** Returns the user's preferred unit: "lb" or "kg". */
function getUnit() { return localStorage.getItem("unit") || "lb"; }

/** The display label for the current unit. */
function unitLabel() { return getUnit() === "kg" ? "kg" : "lbs"; }

/** Convert a stored lbs value to the display unit. */
function toDisplayWeight(lbs) {
  if (lbs == null) return lbs;
  return getUnit() === "kg" ? Math.round(lbs / 2.20462 * 2) / 2 : lbs;  // nearest 0.5 kg
}

/** Convert a value from the current display unit back to lbs for storage. */
function fromInputWeight(val) {
  const n = parseFloat(val);
  if (isNaN(n) || n === 0) return null;
  return getUnit() === "kg" ? Math.round(n * 2.20462 * 2) / 2 : n;  // nearest 0.5 lb
}

/** Format a stored lbs value as a readable string in the current unit. */
function displayWeight(lbs) {
  if (lbs == null) return "—";
  return `${toDisplayWeight(lbs)} ${unitLabel()}`;
}

/** Step attribute for weight inputs in the current unit. */
function weightInputStep() { return getUnit() === "kg" ? "0.5" : "2.5"; }

/**
 * Wire up all .unit-toggle buttons on the page.
 * onToggle() is called after the unit changes so the page can re-render.
 */
function initUnitToggle(onToggle) {
  function syncButtons() {
    document.querySelectorAll(".unit-toggle").forEach(b => {
      b.textContent = getUnit() === "kg" ? "kg" : "lbs";
    });
  }
  syncButtons();
  document.querySelectorAll(".unit-toggle").forEach(btn => {
    btn.addEventListener("click", () => {
      localStorage.setItem("unit", getUnit() === "kg" ? "lb" : "kg");
      syncButtons();
      if (onToggle) onToggle();
    });
  });
}

/**
 * Attach autocomplete to an input element using the canonical exercise library.
 * onSelect(item) is called with {id, name, category} when the user picks one.
 */
async function attachLibraryAutocomplete(input, listEl, onSelect) {
  const library = await getLibrary();
  let activeIdx = -1;

  function close() {
    listEl.classList.add("hidden");
    listEl.innerHTML = "";
    activeIdx = -1;
  }

  function renderMatches(q) {
    if (!q) { close(); return; }
    const matches = library.filter(e => e.name.toLowerCase().includes(q.toLowerCase())).slice(0, 12);
    if (!matches.length) { close(); return; }
    activeIdx = -1;
    listEl.innerHTML = matches.map((m, i) =>
      `<li class="autocomplete-item" data-idx="${i}" data-id="${m.id}" data-name="${escapeHtml(m.name)}">${escapeHtml(m.name)}<small style="color:var(--text-muted);margin-left:.4rem">${m.category}</small></li>`
    ).join("");
    listEl.classList.remove("hidden");
    listEl.querySelectorAll(".autocomplete-item").forEach(li => {
      li.addEventListener("mousedown", ev => {
        ev.preventDefault();
        const item = library.find(e => e.id === parseInt(li.dataset.id));
        if (item) {
          input.value = item.name;
          onSelect(item);
        }
        close();
      });
    });
  }

  input.addEventListener("input", () => renderMatches(input.value.trim()));
  input.addEventListener("keydown", e => {
    const items = [...listEl.querySelectorAll(".autocomplete-item")];
    if (listEl.classList.contains("hidden") || !items.length) return;
    if (e.key === "ArrowDown") { e.preventDefault(); activeIdx = Math.min(activeIdx + 1, items.length - 1); }
    else if (e.key === "ArrowUp") { e.preventDefault(); activeIdx = Math.max(activeIdx - 1, -1); }
    else if (e.key === "Enter" && activeIdx >= 0) {
      e.preventDefault();
      const item = library.find(e => e.id === parseInt(items[activeIdx].dataset.id));
      if (item) { input.value = item.name; onSelect(item); }
      close();
      return;
    } else if (e.key === "Escape") { close(); return; }
    items.forEach((li, i) => li.classList.toggle("active", i === activeIdx));
    if (activeIdx >= 0) items[activeIdx].scrollIntoView({ block: "nearest" });
  });
  input.addEventListener("blur", () => setTimeout(close, 150));
  input.addEventListener("focus", () => { if (input.value.trim()) renderMatches(input.value.trim()); });
}
