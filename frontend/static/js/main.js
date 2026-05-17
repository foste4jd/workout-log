// iOS Safari: `:active` only fires reliably with a touchstart listener present.
document.addEventListener('touchstart', function(){}, {passive: true});

/**
 * Shared API helper — automatically attaches JWT and throws on error.
 */
async function api(url, method = "GET", body = null) {
  const res = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: body ? JSON.stringify(body) : null,
  });

  if (res.status === 401) {
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
      const newUnit = getUnit() === "kg" ? "lb" : "kg";
      localStorage.setItem("unit", newUnit);
      syncButtons();
      // Persist to server (fire-and-forget)
      api("/api/users/me", "PATCH", { unit: newUnit }).catch(() => {});
      if (onToggle) onToggle();
    });
  });
}

/**
 * Attach autocomplete to an input element using the canonical exercise library.
 * onSelect(item) is called with {id, name, primary_muscle, ...} when the user picks one.
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
    listEl.innerHTML = matches.map((m, i) => {
      const tag = m.primary_muscle || m.movement_pattern || "";
      return `<li class="autocomplete-item" data-idx="${i}" data-id="${m.id}" data-name="${escapeHtml(m.name)}">${escapeHtml(m.name)}<small style="color:var(--text-muted);margin-left:.4rem">${escapeHtml(tag)}</small></li>`;
    }).join("");
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

// ── Auth ─────────────────────────────────────────────────────────────────────

/** Wire up #logout-btn. Safe to call even if the button is absent. */
function initLogout() {
  const btn = document.getElementById("logout-btn");
  if (!btn) return;
  btn.addEventListener("click", async () => {
    try { await api("/api/users/logout", "POST"); } catch (_) {}
    window.location.href = "/login";
  });
}

// ── Active program widget ─────────────────────────────────────────────────────

/** Populate #active-prog-strip if the user has an active program run. */
async function initActiveProgramWidget() {
  const strip = document.getElementById("active-prog-strip");
  if (!strip) return;
  try {
    const run = await api("/api/program-runs/active");
    if (!run || !run.program) return;
    const linkEl = document.getElementById("active-prog-link");
    const weekEl = document.getElementById("active-prog-week");
    if (!linkEl) return;
    linkEl.textContent = run.program.name.toUpperCase();
    linkEl.href = `/programs/${run.program.id}`;
    const wk = run.current_week || "?";
    const total = run.program.total_weeks || "?";
    weekEl.textContent = `Week ${wk} of ${total}`;
    strip.style.display = "flex";
  } catch (_) {}
}

// ── Toast notifications ───────────────────────────────────────────────────────

/**
 * Show a brief toast message.
 * type: "success" | "error" | "info"  (default: "info")
 * duration: ms before auto-dismiss  (default: 3000)
 */
function showToast(message, type = "info", duration = 3000) {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  container.appendChild(toast);

  requestAnimationFrame(() => toast.classList.add("toast-visible"));

  setTimeout(() => {
    toast.classList.remove("toast-visible");
    toast.addEventListener("transitionend", () => toast.remove(), { once: true });
  }, duration);
}

// ── Modal helpers ─────────────────────────────────────────────────────────────

/** Open a modal by id. Adds .modal-open to <body> to prevent scroll. */
function openModal(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.add("open");
  document.body.classList.add("modal-open");
  el.addEventListener("click", _modalBackdropHandler);
}

/** Close a modal by id. */
function closeModal(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.remove("open");
  document.body.classList.remove("modal-open");
  el.removeEventListener("click", _modalBackdropHandler);
}

function _modalBackdropHandler(e) {
  if (e.target === e.currentTarget) closeModal(e.currentTarget.id);
}

// ── Bottom-sheet helpers ──────────────────────────────────────────────────────

/** Slide a bottom sheet into view. */
function openSheet(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.add("open");
  document.body.classList.add("sheet-open");
}

/** Dismiss a bottom sheet. */
function closeSheet(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.remove("open");
  document.body.classList.remove("sheet-open");
}

// ── Inline confirm ────────────────────────────────────────────────────────────

/**
 * Replace the contents of cellEl with an inline "message [Yes] [No]" prompt.
 * onConfirm() is called if the user clicks Yes.
 * The cell is restored on No (or if onCancel is provided, that runs first).
 */
function confirmInline(cellEl, onConfirm, message = "Delete?", onCancel = null) {
  const original = cellEl.innerHTML;

  cellEl.innerHTML = `
    <span class="confirm-inline-msg">${escapeHtml(message)}</span>
    <button class="btn btn-danger btn-sm confirm-inline-yes">Yes</button>
    <button class="btn btn-ghost btn-sm confirm-inline-no">No</button>
  `;

  cellEl.querySelector(".confirm-inline-yes").addEventListener("click", () => {
    onConfirm();
  });

  cellEl.querySelector(".confirm-inline-no").addEventListener("click", () => {
    if (onCancel) onCancel();
    cellEl.innerHTML = original;
  });
}
