# WorkoutLog — Product Roadmap

Last updated: 2026-04-17
Source: Full multi-perspective codebase review (security, architecture, performance, UX) — two full passes

---

## How to use this file

Items are grouped by phase, then domain. Within each group, items are ordered by priority.
Status: `[ ]` = not started · `[~]` = in progress · `[x]` = done

---

## ✅ Completed

- [x] Rate limit `POST /api/users/login` and `POST /api/users/register` (Flask-Limiter, 5/min per IP)
- [x] Remove `SECRET_KEY`/`JWT_SECRET_KEY` fallback values — server exits on boot if missing in production
- [x] Move JWT from `localStorage` to `HttpOnly SameSite=Strict` cookie
- [x] Add `anthropic` to `requirements.txt` and implement `AnthropicProvider`
- [x] Replace `_run_migrations()` with Flask-Migrate / Alembic — baseline revision stamped, future schema changes tracked via `flask db migrate`
- [x] Paginate `GET /api/workouts/` — `?page=&limit=` supported; frontend fetches all pages for calendar
- [x] Rewrite stats endpoint to use SQL aggregation (`COUNT`, `SUM`, `MAX`, `GROUP BY`) — no more full table loads
- [x] Rest timer on session page — 60/90/120/180s presets, auto-starts on circle tap, vibrates on completion
- [x] Last-session weight/reps hint in set edit sheet — `GET /api/exercises/last-session?name=`
- [x] Split-tap onboarding hint — dismissible overlay on first session load, stored in `localStorage`
- [x] Persist unit preference (`lb`/`kg`) server-side — `unit` column on `User`, `PATCH /api/users/me`, restored on login

---

## Phase 1 — Foundation (do before any new features or schema changes)

These are correctness and safety items. Every new feature built before these is built on sand.

### 🏗️ Architecture & Data Integrity

| Priority | Item | Notes |
|----------|------|-------|
| P0 | **Replace `_run_migrations()` with Flask-Migrate / Alembic** | Bare `ALTER TABLE` in `try/except` on every startup — silent failures, no version tracking, no rollback. Every future schema change depends on this being solid first. |
| P1 | **Standardize `weight_lb` across all set models** | `ExerciseSet.weight_lb` vs `WorkoutTemplateSet.weight` — same field, different names. Renamed explicitly in `create_session_from_template()`. Silent bug risk at template→session boundary. |
| P1 | **Persist AI rate limit counter in DB** | `_daily_counts` is a process-local dict — resets on restart. In multi-worker deploy, each worker has an independent counter (4× budget with 4 workers). Move to a DB column or Redis key. |
| P1 | **Add `openai` to `requirements.txt`** | The OpenAI provider is still the default. A fresh `pip install -r requirements.txt` crashes on first AI call. |
| P2 | **Replace silent `except Exception: pass` in pattern detection** | `detect_patterns_on_save` swallows all exceptions. Any bug in AI pattern detection is invisible. Replace with `app.logger.exception()`. |
| P2 | **Add startup env var validation** | Extend secret key enforcement to AI config: `AI_MAX_DAILY_REQUESTS=0` silently disables AI for all users. |

- [x] Migrate `_run_migrations()` to Flask-Migrate / Alembic
- [x] Rename `WorkoutTemplateSet.weight` → `weight_lb`
- [ ] Persist AI daily rate limit counter in DB (not process dict)
- [ ] Add `openai` to `requirements.txt`
- [ ] Replace silent `except Exception: pass` with structured logging
- [ ] Add startup validation for AI config env vars

### ⚡ Performance & Scale

| Priority | Item | Notes |
|----------|------|-------|
| P0 | **Paginate workout list endpoint** | `Workout.query.filter_by(user_id=...).all()` loads full history into memory. A user with 2+ years of training (700+ workouts) will experience a hung page. Add `?page=&limit=`. |
| P1 | **Move stats aggregation to SQL** | Stats endpoint loads all workouts + exercises into Python and iterates manually. `COUNT`, `MAX`, `SUM`, `GROUP BY` belong in SQLite. Faster and less memory. |
| P2 | **Add `joinedload` on exercise/set queries** | SQLAlchemy lazy-loads `Exercise.sets` in a loop. N+1 queries on every session page load. Three-line fix with `joinedload(Exercise.sets)`. |
| P3 | **Document SQLite → Postgres migration path** | SQLite has no concurrent write support. Not urgent for single-user. Required before multi-worker or hosted deployment. |

- [x] Paginate `GET /api/workouts/` endpoint (`?page=&limit=`)
- [x] Rewrite stats endpoint to use SQL aggregation instead of Python loops
- [ ] Add `joinedload`/`selectinload` to eliminate N+1 in exercise/set queries
- [ ] Document SQLite → Postgres migration path

---

## Phase 2 — High-Impact UX Wins (low effort, high training-day value)

These do not require schema changes and have outsized impact on daily usability.

| Priority | Item | Notes |
|----------|------|-------|
| P1 | **Rest timer** | The single most glaring omission. Every serious lifting app has one. Client-side only — no backend. 60/90/120/180s presets. Starts on set completion. Without this, the app loses to a basic stopwatch in the gym the moment a set is done. |
| P1 | **Last-session weight hint** | When entering weight for an exercise, surface "Last: 185×5" inline. Data already exists — it's just not shown at the point where the decision is made. Biggest planning friction point — felt on every set. |
| P1 | **Destructive action confirmations** | Delete workout and remove exercise are instant and irreversible. One accidental tap wipes training history. Add confirmation dialogs or undo toasts. This is a trust issue, not just a UX issue. |
| P1 | **Split-tap onboarding hint** | Circle = mark done / row = edit is the right interaction model but completely undiscoverable. One-time tooltip on first session load (remembered in `localStorage`, never shown again). |
| P2 | **Persist unit preference (lb/kg) server-side** | Currently `localStorage`-only. Switching devices resets the unit. 10-minute fix: add `unit` column to `User` model. |
| P2 | **Session live duration counter** | Show elapsed time since session started in the action bar. No backend needed — store start time in `sessionStorage`. |
| P2 | **Empty-state onboarding** | New users land on a blank workouts list with no guidance. Add copy + CTAs: "Log your first workout", "Browse templates", "Let AI plan your session". |
| P2 | **Global session set-progress indicator** | Per-exercise counter (2/5) exists. Add total to the bottom action bar: "11 / 23 sets". |

- [x] Add client-side rest timer to session page (presets + auto-start on set done)
- [x] Show last-session weight/reps hint inline on weight inputs
- [x] Add confirmation dialogs for workout delete and exercise remove
- [x] Add first-session split-tap onboarding hint (dismissible, `localStorage`-remembered)
- [x] Persist unit preference (lb/kg) on `User` model server-side
- [x] Add session elapsed duration counter to action bar
- [ ] Write empty-state copy with onboarding CTAs on workouts page
- [ ] Add global set-progress counter to session action bar ("11 / 23 sets")

---

## Phase 3 — History & Insight (makes logged data actually useful)

Six months of training logs are worthless if you can't query them.

| Priority | Item | Notes |
|----------|------|-------|
| P1 | **Per-exercise history page/drawer** | All logged sets for a given exercise over time — date, weight, reps, % for each session. Accessible from session and log pages. |
| P1 | **Per-exercise progression chart** | Weight and/or volume over last N sessions as a simple line chart. Answers the actual training question: "Am I getting stronger?" |
| P1 | **Workout history search and filter** | Filter by exercise name, date range, workout title. The flat chronological list is unusable for review after 2+ months. |
| P2 | **Dashboard revamp: actionable insights** | Replace vanity stats (total workouts: 47) with training signals: "Your squat has stalled 4 sessions", "No posterior chain work in 9 days", "You're trending up on bench". |
| P2 | **Personal records with context** | Best set per exercise with date, session title, and adjacent context (what else was trained that day). |
| P3 | **Workout data export** | CSV or JSON export of full training history. If users can't get their data out, they won't trust the app with their data long-term. |

- [x] Build per-exercise history view (all logged sets over time)
- [x] Add per-exercise weight/volume progression chart
- [x] Add search and filter to workout history page
- [ ] Revamp dashboard to surface actionable training insights
- [ ] Build personal records section with date and context
- [ ] Add training history export (CSV or JSON)

---

## Phase 4 — Program Structure (required to serve serious lifters)

The single highest-value missing product concept. Without this, serious programmers still need a spreadsheet.

| Priority | Item | Notes |
|----------|------|-------|
| P1 | **`Program` model** | Named training block (e.g. "5/3/1 Wave 1") with ordered weeks and a start date. |
| P1 | **`ProgramWeek` model** | Ordered sessions within a week, each referencing a template. Defines the schedule: Mon = Squat A, Wed = Bench B, Fri = Deadlift C. |
| P1 | **Weekly schedule view** | Calendar-style or list view: "This week — Mon: Squat A (done), Wed: Bench B (planned), Fri: Deadlift C". |
| P2 | **Auto-advance to next session** | After completing a session in a program, offer "Start next session" — no template hunting required. |
| P2 | **Program progress indicator** | "Week 4 of 12, Session 2 of 3 this week." Visible on session page and weekly view. |
| P3 | **AI suggestions surfaced inline** | Structured suggestions (recommended load, deload cue) as inline hints at weight input rather than behind the AI bottom sheet chat interface. |

- [x] Design and build `Program` model (block → weeks)
- [x] Design and build `ProgramWeek` model (week → sessions via `ProgramDay`)
- [x] Build weekly schedule view
- [ ] Add auto-advance to next session within a program
- [ ] Add program progress indicator to session page
- [ ] Surface AI load recommendations inline at weight input

---

## Phase 5 — Security Hardening (required before any public exposure)

| Priority | Item | Notes |
|----------|------|-------|
| P1 | **Add Content-Security-Policy header** | No CSP currently. Inline `<script>` blocks throughout templates require nonces or extraction to static files. Add via Flask `after_request`. |
| P1 | **Document HTTPS + HSTS setup** | `JWT_COOKIE_SECURE` is correctly gated on `FLASK_ENV`. Reverse proxy (nginx, Caddy) with HTTPS is required for any non-localhost deployment. |
| P2 | **Rate limiter backed by Redis** | In-memory storage resets on restart and is per-process. Acceptable for personal use, required for multi-user. |
| P2 | **Input length caps on all text fields** | Title, notes, exercise name, prompt — all currently uncapped. No injection risk (ORM), but no bounds on DB row size or AI token spend. |
| P2 | **Refresh token mechanism** | 30-day access token is a workaround for lacking refresh tokens. Short-lived access (15 min) + long-lived refresh (7 day) is the correct pattern. |
| P3 | **Normalize auth error messages** | Confirm login returns the same error for wrong username and wrong password (enumeration prevention). Currently OK but worth a formal audit. |

- [x] Add `Content-Security-Policy` response header (with nonces or extracted scripts)
- [ ] Document HTTPS reverse proxy setup + HSTS header
- [ ] Move rate limiter storage to Redis for multi-user deployments
- [ ] Add input length validation on all user-supplied text fields
- [ ] Implement refresh token mechanism
- [ ] Audit and normalize auth error messages

---

## Phase 6 — Sharing & Coaching (only after single-user experience is excellent)

Overkill until Phases 1–3 are complete. The single-user loop must be excellent before sharing it.

| Priority | Item | Notes |
|----------|------|-------|
| P1 | **Public template share link** | Read-only URL for a program or template. No auth required to view. |
| P2 | **Coach/client model** | Multi-user with a coach role. Coach can view and edit client sessions and assign programs. |
| P2 | **Client program assignment** | Coach assigns a `Program` to a client. Client sees it in their weekly view. |
| P3 | **Push notifications** | Rest timer push notification, session reminder. Requires PWA or native shell. |
| P3 | **Social/follow features** | Out of scope until coaching model is stable. |

- [ ] Build public template/program share link (read-only)
- [ ] Design and build coach/client multi-user model
- [ ] Build client program assignment flow
- [ ] Add push notification support (rest timer, reminders)

---

## Current Priority Order (act on these next)

Items 1–14 are complete. Remaining priorities:

| # | Item | Phase | Why now |
|---|------|-------|---------|
| 1 | ~~Flask-Migrate / Alembic~~ | 1 | ✅ Done |
| 2 | ~~Paginate workout list~~ | 1 | ✅ Done |
| 3 | ~~Rest timer~~ | 2 | ✅ Done |
| 4 | ~~Last-session weight hint~~ | 2 | ✅ Done |
| 5 | ~~Destructive action confirmation~~ | 2 | ✅ Done |
| 6 | ~~Stats aggregation → SQL~~ | 1 | ✅ Done |
| 7 | ~~Split-tap onboarding hint~~ | 2 | ✅ Done |
| 8 | ~~Persist unit preference server-side~~ | 2 | ✅ Done |
| 9 | ~~Rename `WorkoutTemplateSet.weight` → `weight_lb`~~ | 1 | ✅ Done |
| 10 | ~~Per-exercise history + progression chart~~ | 3 | ✅ Done |
| 11 | ~~Workout history search and filter~~ | 3 | ✅ Done |
| 12 | ~~Session elapsed duration counter~~ | 2 | ✅ Done |
| 13 | ~~Program / week / cycle model~~ | 4 | ✅ Done |
| 14 | ~~Add `Content-Security-Policy` header~~ | 5 | ✅ Done |

---

## Phase 7 — Design System Upgrade

Sourced from full UI/UX audit (2026-04-16). Every page was reviewed against the confirmed design direction (focused/exact/disciplined, Linear+Stripe references). See `.impeccable.md` for the full design context.

### 🔴 Global — Apply to every page

| Priority | Item | Notes |
|---|---|---|
| P0 | **Replace Inter with Barlow Semi Condensed + Hanken Grotesk** | All pages still load Inter. Login is the only page on the new type system. |
| P0 | **Migrate color tokens to OKLCH** | All pages use old hex palette (`#08111E`, `#4090FF`). OKLCH tokens defined in `.impeccable.md` and implemented on login. |
| P0 | **Replace `alert()` / `confirm()` with inline errors + undo toasts** | `session.html` uses `alert(err.message)`; `maxes.html` uses native `confirm()`. Browser dialogs break the theme and signal "prototype." Use inline error states and a lightweight dismiss-able toast for destructive confirmations. |
| P0 | **Replace unicode emoji action icons with SVGs** | `workouts.html` and `programs.html` use `&#9654;` `&#10697;` `&#128278;` `&#128465;` `&#9998;` as action buttons. Renders as emoji on iOS. Replace with the SVG icon pattern used everywhere else in the app. |
| P1 | **Fix bottom nav label: "Profile" → "Stats"** | `/dashboard` is a stats page, not a profile/account page. Mislabeled on every page. |
| P1 | **Remove gradient text from `index.html`** | `hero h1 span` uses `background-clip: text` with a gradient — hard banned in design system. |
| P1 | **Eliminate inline `style=""` attributes** | Hundreds of scattered inline styles make the design unmaintainable. Move to CSS classes and tokens. |
| P2 | **Fix `programs.html` navbar logo** | `<span class="nav-logo">Programs</span>` — bug. Should be "WorkoutLog". |
| P2 | **Standardize `%TM` / `% of TM` / `%` column header** | Three different labels for the same concept across log, session, and templates. Pick one. |

### 🟠 Session Page (`/session`) — highest priority screen

| Priority | Item | Notes |
|---|---|---|
| P0 | **Move elapsed timer out of the action bar** | Currently sandwiched between "+ Add Exercise" and "Complete Workout" buttons. Move to the session header next to the title. |
| P0 | **Remove "Edit" text hint from every set row** | 12+ rows each showing "Edit" on the right — banner blindness kills it. Tap affordance should come from row active state, not a text label. |
| P1 | **Fix rest timer preset labels** | `1m | 1:30 | 2m | 3m` is inconsistent. Use `1:00 | 1:30 | 2:00 | 3:00` throughout. |
| P1 | **Remove `backdrop-filter: blur(12px)` from action bar** | Decorative glassmorphism. Replace with solid `var(--surface)` background. |
| P1 | **Demote set type pills in edit sheet** | Type pills (Working/Warmup/AMRAP/EMOM/Failure) are the first thing in the sheet but changed <5% of the time. Collapse to a secondary section below reps/weight inputs. |
| P1 | **Replace split-tap onboarding modal** | 1.2s-delayed full-screen overlay breaks the first session experience. Replace with a single inline hint on the first set row only, auto-dismissed on first circle tap. |
| P2 | **Fix `set-sub` arrow glyph** | `75% TM → 225 lbs` — the `→` is visual clutter. Use `·` separator: `75% · 225 lbs`. |
| P2 | **Remove italic exercise notes** | `.ex-block-notes` uses `font-style: italic` at `.78rem` on dark background — unreadable under gym lighting. |

### 🟠 Dashboard (`/dashboard`)

| Priority | Item | Notes |
|---|---|---|
| P1 | **Break 4-equal-stat card pattern** | All 4 stats use `stat-value-accent` at identical visual weight. Promote "This Week" and "Day Streak" as primary (large type). Demote "Total Workouts" and "Hours Trained" to secondary context. |
| P1 | **Add week context to the page** | No date or time orientation anywhere on the page. Add current week date range as a sub-heading. |
| P2 | **Remove heatmap legend "Less / More" labels** | Self-evident from the visual. Adds noise. |
| P2 | **Rename "Best Recorded Lifts" → "Training Maxes"** | The PR table shows best lift by weight, but the data most relevant to serious lifters is their training maxes. Consider merging or clarifying. |

### 🟠 History (`/workouts`)

| Priority | Item | Notes |
|---|---|---|
| P0 | **Fix `var(--text-primary)` in search input** | Token does not exist in the design system — should be `var(--text)`. Live bug on the search input. |
| P1 | **Reduce 5-action card cluster to 1** | Open ▶, Copy ⧉, Save Template 🔖, Edit ✏️, Delete × on every card. Primary action is Open. The rest belong inside the session view. Remove Copy, Save Template, Edit, and Delete from the history card. |
| P1 | **Scroll to day panel on mobile after calendar tap** | Selecting a date updates the panel below the fold without scrolling — users don't see the content change. |
| P2 | **Unify search result card with day panel card** | Search results render stripped-down cards (no exercises, no actions). Inconsistent with the day panel card. |

### 🟡 Log Page (`/log`)

| Priority | Item | Notes |
|---|---|---|
| P1 | **Separate AI entry point from metadata strip** | Date, duration, notes, and AI button are peers in the meta strip. AI is a fundamentally different action (generate) vs the others (record). Give it a distinct entry point above or below the exercise list. |
| P1 | **Promote `+ Add Exercise` to primary button** | Currently a ghost button. Adding exercises is the primary task on this page — it should have primary visual weight. |
| P1 | **Conditionally show `%` column** | The `%` column renders on every set row even when no training max is set. Only show it when `trainingMaxMap` has an entry for that exercise. |
| P2 | **Strengthen `log-title-input` hierarchy** | The title input looks like a form field. It should read as the page's primary heading — larger type, lighter placeholder, clear visual prominence. |

### 🟡 Templates (`/templates`)

| Priority | Item | Notes |
|---|---|---|
| P1 | **Replace `<select>` set type with cycling badge** | The builder uses a native OS `<select>` dropdown for set type. Log and session use a cycling badge. Unify to the badge pattern. |
| P2 | **Move builder out of a modal** | 95vw × 90vh scrollable modal for complex template editing. Should be a full-page route (`/templates/new`, `/templates/:id/edit`). |
| P2 | **Add exercise reorder controls** | No way to reorder exercises in a template. Minimum viable: up/down arrow buttons per exercise. |

### 🟡 Training Maxes (`/maxes`)

| Priority | Item | Notes |
|---|---|---|
| P1 | **Fix edit-scroll disorientation** | Clicking Edit on a row populates the form at the top of the page without scrolling or signaling. Scroll to the form on edit, or move to an inline row-edit pattern. |
| P2 | **Remove or collapse the explanatory paragraph** | "Your training max is the weight used for..." is useful once, noise on every visit. Collapse it or show only on empty state. |
| P2 | **Hide Notes column when empty** | The Notes column is `—` for most rows. Remove it from the table; surface notes only inline when present. |
| P2 | **Unify Edit/Delete button styles** | Edit is a text button (`.btn-ghost.btn-sm`); Delete is an icon button (`btn-icon`). Same row, different patterns. |

---

### Phase 7 — Priority Order

| # | Item | Page | Impact | Status |
|---|---|---|---|---|
| 1 | Apply Barlow SC + Hanken Grotesk to all pages | Global | Visual coherence | ✅ Done |
| 2 | Migrate color tokens to OKLCH | Global | Visual coherence | ✅ Done |
| 3 | Replace `alert()`/`confirm()` with inline errors | Global | Trust / polish | ✅ Done |
| 4 | Replace unicode emoji icons with SVGs | Global | Polish | ✅ Done (workouts.html) |
| 5 | Fix bottom nav "Profile" → "Stats" | Global | Navigation clarity | ✅ Done |
| 6 | Remove gradient text (`index.html`, `auth-logo`) | Landing | Banned pattern | ✅ Done |
| 7 | Remove `backdrop-filter` (navbar, bottom-nav, session bar) | Global | Design system | ✅ Done |
| 8 | Remove italic exercise notes | Session | Readability | ✅ Done |
| 9 | Move elapsed timer to session header | Session | Mid-workout UX | ✅ Done |
| 10 | Remove "Edit" hints from session set rows | Session | Mid-workout UX | ✅ Done |
| 11 | Fix rest timer preset labels to `1:00 \| 1:30 \| 2:00 \| 3:00` | Session | Mid-workout UX | ✅ Done |
| 12 | Active set highlighting + progress bar | Session | Mid-workout UX | ✅ Done |
| 13 | Simplified edit sheet (2 large inputs, % computed, type collapsed) | Session | Mid-workout UX | ✅ Done |
| 14 | Last-session data shown inline in exercise block | Session | Mid-workout UX | ✅ Done |
| 15 | Fix `var(--text-primary)` bug in search input | History | Live bug | ✅ Done |
| 16 | Fix programs navbar logo bug | Programs | Bug | ✅ Done |
| 17 | Remove banned `border-left` stripes → `border-top` | Global | Design system | ✅ Done |
| 18 | Fix `.exercise-bar-fill` gradient → solid | Dashboard | Banned pattern | ✅ Done |
| 19 | Remove `text-align: center` from stat cards + day panel | Global | Layout | ✅ Done |
| 20 | Build shared template system (`_base.html`, `_navbar.html`, `_bottom_nav.html`, `_macros.html`) | Global | DRY, consistency | ✅ Done |
| 21 | Add shared JS helpers (`initLogout`, `showToast`, `openModal/closeModal`, `openSheet/closeSheet`, `confirmInline`) | Global | Component system | ✅ Done |
| 22 | Full `main.css` design elevation pass (Linear/Stripe quality) | Global | Visual quality | ✅ Done |
| 23 | Add micro-interactions system (iOS `:active` fix, `focus-visible`, `check-done` animation, `prefers-reduced-motion`) | Global | Polish / gym UX | ✅ Done |
| 24 | Migrate `dashboard.html` to `_base.html` template inheritance | Dashboard | DRY | ✅ Done |
| 25 | Migrate `workouts.html` modal system from `.hidden` → `.open` | History | Component system | ✅ Done |
| 26 | Reduce workout card action cluster from 5 → 1 | History | Clarity | `[ ]` |
| 27 | Break 4-equal-stat card pattern on dashboard | Dashboard | Information hierarchy | `[ ]` |
| 28 | Separate AI entry from metadata strip on log page | Log | Cognitive clarity | `[ ]` |
| 29 | Conditionally show `%` column on set rows | Log | Density / noise | `[ ]` |
| 30 | Replace `<select>` set type with cycling badge in template builder | Templates | Consistency | `[ ]` |
| 31 | Scroll to day panel on mobile after calendar tap | History | Mobile UX | `[ ]` |
| 32 | Add week context / date range to dashboard header | Dashboard | Orientation | `[ ]` |
| 33 | Strengthen `log-title-input` hierarchy | Log | Visual hierarchy | `[ ]` |
| 34 | Move template builder out of modal → full-page route | Templates | UX | `[ ]` |
| 35 | Migrate remaining pages to `_base.html` template inheritance | Global | DRY | `[ ]` |

### Phase 7 — Log Page Flow Improvements (sourced from 30-second flow friction audit, 2026-04-17)

| # | Item | Page | Impact | Status |
|---|---|---|---|---|
| 36 | Replace native date `<input>` with custom OKLCH calendar popover | Log | Gymability, dark theme | ✅ Done |
| 37 | Auto-default title to date string; async AI title generation from exercise names | Log | Reduces blank-field friction | ✅ Done |
| 38 | Post-save "Plan next day →" inline link for future-dated workouts | Log | 5-day planning flow (no navigation) | ✅ Done |
| 39 | Quick-set parser: natural language ("3 sets of 5") + per-set weights ("3×5 at 65% 70% 75%") | Log | Data entry speed | ✅ Done |
| 40 | Always-visible append-mode quick-set input (never hidden after first entry) | Log | Discoverability | ✅ Done |
| 41 | "Repeat last workout" shortcut on log page — one tap to load previous session's exercises | Log | Planning speed (friction item F5) | `[ ]` |
| 42 | Date quick-pills (+1 through +7 days) below the calendar popover | Log | Rapid week planning (friction item F8) | `[ ]` |
| 43 | Bulk week planning flow — assign a template to multiple days at once from the log page | Log / Programs | Planning 5+ workouts (friction items F7, F10) | `[ ]` |
