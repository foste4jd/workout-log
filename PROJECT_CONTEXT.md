# Barpath — Project Context

Use this document to give an AI assistant full context when asking for feature ideas, implementation help, or code improvements. It is organized by domain so you can point an AI at only the section relevant to your task.

---

## What This App Is

Barpath is a personal strength-training tracker. It is a **single-user-per-account** tool. Each user logs their own sessions, tracks exercises with sets/reps/weight/percentages, manages training maxes for percentage-based programming, uses AI-generated workout suggestions, and reviews stats on a dashboard.

It is **not** a social app — no sharing, no public profiles, no feed. The goal is a clean, fast, self-hosted utility for serious training. The UX philosophy is: **workout-first, fewer decisions, faster flow, calm UI**. Think premium utility, not feature-heavy product.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.13 |
| Web framework | Flask (app factory pattern) |
| ORM | SQLAlchemy (via Flask-SQLAlchemy) |
| Auth | Flask-JWT-Extended (JWT stored in `HttpOnly SameSite=Strict` cookie) |
| Password hashing | Flask-Bcrypt |
| Database | SQLite (`workout_log.db`) |
| Frontend | Vanilla HTML, CSS, JavaScript — no framework, no build step |
| Templates | Jinja2 (server renders HTML shell; JS fetches data from API) |
| AI | Anthropic Claude API (via `anthropic` Python SDK) |

No external services beyond the AI API. Everything else runs locally via `python -m backend.app`.

---

## Project Structure

```
workout-log/
├── backend/
│   ├── app.py                     # App factory (create_app), blueprint registration
│   ├── config.py                  # Config class (reads .env)
│   ├── ai_config.py               # AI feature flags and cost controls
│   ├── db/
│   │   └── database.py            # SQLAlchemy db instance
│   ├── models/
│   │   ├── user.py                # User (includes `timezone` field, auto-detected from browser)
│   │   ├── workout.py             # Workout (session record)
│   │   ├── exercise.py            # Exercise (belongs to a Workout)
│   │   ├── exercise_set.py        # ExerciseSet (belongs to an Exercise)
│   │   ├── exercise_library.py    # ExerciseLibrary (global catalogue)
│   │   ├── workout_template.py    # WorkoutTemplate + Exercise + Set (3 tables)
│   │   ├── training_max.py        # TrainingMax (per user per library exercise)
│   │   ├── personal_max.py        # PersonalMax (auto-tracked best lift by name)
│   │   ├── ai_knowledge.py        # AIKnowledge (AI memory records)
│   │   ├── program.py             # Program + ProgramDay (training cycle model)
│   │   ├── user_profile.py        # UserProfile (one-to-one: experience, goal, intensity style, restrictions)
│   │   └── bodyweight_entry.py    # BodyweightEntry (time-series, always stored in kg)
│   ├── services/
│   │   ├── workout_service.py     # Workout CRUD
│   │   ├── exercise_service.py    # Exercise + set CRUD, auto-PR logic
│   │   ├── template_service.py    # Template CRUD + start-from-template
│   │   ├── training_max_service.py # Training max CRUD
│   │   ├── max_service.py         # Personal max CRUD
│   │   ├── ai_trainer_service.py  # AI suggest + accept + save-template + memory
│   │   ├── program_service.py     # Program CRUD + start-day-as-session
│   │   └── profile_service.py     # Athlete profile CRUD + bodyweight history
│   └── api/routes/
│       ├── users.py               # Auth: register, login; PATCH /me handles unit + timezone
│       ├── workouts.py            # Workout CRUD + complete + copy + save-as-template
│       ├── exercises.py           # Exercise CRUD + PATCH session-sets + history
│       ├── library.py             # Exercise library
│       ├── templates.py           # Template CRUD + start
│       ├── training_maxes.py      # Training max CRUD
│       ├── maxes.py               # Personal max CRUD
│       ├── stats.py               # Dashboard stats (all boundaries in user's local timezone)
│       ├── ai_trainer.py          # AI suggest + accept + save-template + memory admin
│       ├── programs.py            # Program CRUD + start-day
│       ├── profile.py             # Athlete profile CRUD + bodyweight logging
│       └── views.py               # Page routes (Jinja2 renders)
├── frontend/
│   ├── templates/
│   │   ├── _base.html             # Base template: head, Google Fonts, main.js/css, body scaffold
│   │   ├── _navbar.html           # Top navbar partial (logo, unit toggle, sign-out icon)
│   │   ├── _bottom_nav.html       # Bottom tab bar partial — active state via request.path
│   │   ├── _macros.html           # Jinja2 macros: page_header, form_error, empty_state, tm_badge, modal, sheet
│   │   ├── index.html             # Landing page
│   │   ├── login.html             # Login / register
│   │   ├── log.html               # Log a new workout
│   │   ├── session.html           # Live workout session (elapsed timer, rest timer)
│   │   ├── workouts.html          # Workout history + search bar
│   │   ├── templates.html         # Template library + builder
│   │   ├── maxes.html             # Training max management
│   │   ├── dashboard.html         # Stats + PRs + heatmap (extends _base.html)
│   │   ├── exercise_history.html  # Per-exercise history + SVG progression chart
│   │   ├── programs.html          # Program list + create/edit modal
│   │   ├── program_detail.html    # Weekly schedule view + Edit Schedule mode
│   │   └── ai_memory.html         # AI memory admin (rendered by views.py)
│   └── static/
│       ├── css/main.css           # All styles (design tokens + components)
│       └── js/main.js             # Shared JS (api(), unit toggle, autocomplete, escapeHtml)
├── scripts/
│   └── seed_ppsa_templates.py     # Restore PPSA templates via API (42 templates)
├── seed.py                        # Create demo account + sample data (preserves templates)
└── requirements.txt
```

---

## Data Models

### User
- `id`, `username` (unique), `email` (unique), `password_hash`, `unit` (`"lb"` | `"kg"`, default `"lb"`), `timezone` (IANA tz string, default `"UTC"`, auto-detected from browser)
- Has many: Workouts, WorkoutTemplates, TrainingMaxes, PersonalMaxes, AIKnowledge
- Timezone is silently synced on every authenticated page load via `Intl.DateTimeFormat().resolvedOptions().timeZone`

### UserProfile
- `id`, `user_id` (unique FK → User), `experience_level`, `primary_goal`, `training_frequency_target`, `preferred_intensity_style`, `movement_restrictions`, `updated_at`
- One-to-one with User. Auto-created (all-null) on first access.
- `experience_level`: `"beginner"` | `"intermediate"` | `"advanced"` | `"elite"`
- `primary_goal`: `"strength"` | `"hypertrophy"` | `"powerlifting"` | `"general"` | `"endurance"`
- `preferred_intensity_style`: `"rpe"` | `"percentage"` | `"load"` | `"auto"`
- All fields nullable — user fills them in over time via `/account`
- Injected into AI trainer context via `profile_service.get_profile_context(user_id)` in `build_context()`

### BodyweightEntry
- `id`, `user_id` (FK → User), `weight_kg` (always stored in kg), `recorded_date` (Date), `notes`, `created_at`
- Time-series bodyweight log. Displayed in user's preferred unit (`lb` or `kg`).
- `to_dict(unit)` handles conversion: `weight_kg * 2.20462` for lbs.

### Workout
- `id`, `user_id`, `title`, `notes`, `duration_minutes`, `date`, `status`
- `status`: `"logged"` (post-hoc entry) | `"planned"` (created from template, not yet done) | `"completed"` (session marked done)
- Has many: Exercises (cascade delete)

### Exercise
- `id`, `workout_id`, `name`, `notes`, `exercise_library_id` (nullable FK → ExerciseLibrary)
- Has many: ExerciseSets (cascade delete, ordered by `set_number`)

### ExerciseSet
- `id`, `exercise_id`, `set_number`, `set_type`, `reps`, `weight_lb`, `percent`, `duration_seconds`, `completed`
- `planned_reps`, `planned_weight_lb`, `planned_percent` — template-sourced values preserved at session creation; never overwritten by live edits
- `set_type`: `"warmup"` | `"working"` | `"amrap"` | `"emom"` | `"failure"`
- `percent`: the planned % of training max (stored, not recomputed — source of truth)
- `completed`: `True` by default for logged sets; toggled per-set during live sessions
- `weight_lb` and `reps` are nullable (bodyweight / cardio compatible)

### ExerciseLibrary
- `id`, `name` (unique), `category`, `is_active`
- Global catalogue shared by all users. Exercises link here for autocomplete, training max resolution, and template building.
- Seeded with ~150+ exercises across categories (Squat, Hinge, Press, Pull, etc.)

### WorkoutTemplate / WorkoutTemplateExercise / WorkoutTemplateSet
- Three-table hierarchy: Template → Exercises → Sets (mirrors Workout → Exercise → ExerciseSet)
- `WorkoutTemplate`: `id`, `user_id`, `name`, `description`, `created_at`, `updated_at`
- `WorkoutTemplateExercise`: `id`, `template_id`, `exercise_id` (FK → ExerciseLibrary), `order_index`, `notes`
- `WorkoutTemplateSet`: `id`, `template_exercise_id`, `set_number`, `set_type`, `reps`, `weight_lb`, `percent`, `duration_seconds`
- **Important**: `weight_lb` (not `weight`) — renamed in migration `0b36035b6e36`. All JS in `templates.html` uses `weight_lb` throughout.
- Templates are keyed to `user_id`. `seed.py` is written to preserve the admin user record (update in-place) so template associations are never orphaned.

### TrainingMax
- `id`, `user_id`, `exercise_id` (FK → ExerciseLibrary), `training_max_weight`, `updated_at`, `notes`
- Unique constraint on `(user_id, exercise_id)` — one record per exercise per user
- **Never auto-updated by logged performance** — only manually set by the user on `/maxes`
- Used by the log and session pages to compute and display `% of TM` per set

### PersonalMax
- `id`, `user_id`, `exercise_name`, `weight_lb`, `is_manual`
- Unique constraint on `(user_id, exercise_name)`
- `is_manual=False`: auto-created/updated by `exercise_service._auto_update_max()` when a set is logged
- `is_manual=True`: user set it explicitly; the system never overwrites it
- Stored by **name string**, not library ID — catches any set even without library linkage

### AIKnowledge
- `id`, `user_id`, `c
- ategory`, `content`, `priority`, `is_active`, `created_at`
- Stores observations the AI makes about the user's training patterns, schedule, injuries, preferences
- `category`: `"schedule"` | `"recovery"` | `"injury"` | `"preferences"` | `"performance_pattern"`
- The AI reads active records when generating workout suggestions to personalize recommendations

### Program / ProgramDay
- `Program`: `id`, `user_id`, `name`, `description`, `total_weeks`, `start_date`, `created_at`
- `ProgramDay`: `id`, `program_id`, `week_number`, `day_order`, `template_id` (nullable FK → WorkoutTemplate), `label`
- A Program is a named training cycle (e.g. "5/3/1 Wave 1"). ProgramDays define the weekly schedule.
- `template_id=NULL` means a rest day; any day with a template can be "started" to create a live session
- Cascade delete: deleting a Program deletes all its ProgramDays
- `start_program_day()` calls `template_service.create_session_from_template()` and redirects to `/session/<id>`

---

## Domain Reference

---

### Domain 1 — Authentication

**What it does**: JWT-based register/login. Single account = single user's training data.

**Flow**:
1. Register: `POST /api/users/register` `{username, email, password}` → user created, cookie set
2. Login: `POST /api/users/login` `{username, password}` → `HttpOnly SameSite=Strict` cookie set
3. All protected routes read JWT from cookie; no `Authorization` header needed
4. JWT identity = `str(user.id)`; routes call `int(get_jwt_identity())`
5. `api()` in `main.js` uses `credentials: "include"` — cookie is sent automatically
6. Logout: `POST /api/users/logout` → `unset_jwt_cookies()`; no client-side token to clear
7. Unit preference (`lb`/`kg`) is stored server-side and restored from `data.user.unit` on login
8. `PATCH /api/users/me` updates unit; `initUnitToggle` calls this automatically on toggle

**Key files**: `backend/api/routes/users.py`, `backend/models/user.py`, `frontend/templates/login.html`

**Future ideas**: Refresh tokens, password change endpoint, account deletion

---

### Domain 2 — Workout Logging (`/log`)

**What it does**: Log a completed workout after the fact, or plan a future one. Not a live timer — just a structured form for recording what you did.

**UX design**:
- Large underline title input at top — **auto-defaults to a date string** (e.g. "Fri, Apr 18") so save is never blocked. Once exercises are added, an **async AI title call** (`POST /api/ai/title`) fires after 900ms of inactivity and overwrites the auto-title with a punchy 2-4 word name (e.g. "Heavy Squat Day"). User edits lock the title permanently.
- Compact meta strip: **custom calendar chip** | duration chip | notes chip | AI button — all inline, no card wrapper
- **Custom calendar popover** (replaces native `<input type="date">`): `position: fixed` OKLCH-styled month grid; keyboard-accessible; 180ms expo-ease enter / 100ms exit. A hidden `<input type="hidden" id="log-date">` preserves all downstream JS compatibility.
- Exercises section is the main content — promoted above everything else
- Each exercise: autocomplete search → sets below it
- Each set row: `# | [type badge] | reps | weight | % | ×`
  - Type badge is a **tappable cycling button** (work → wu → amrap → emom → fail → work)
  - `%` column appears only when a training max exists for that exercise
  - `weight ↔ %` are bidirectionally synced: type one, the other auto-fills
- TM badge shows above sets if training max is set for that exercise
- **Quick-set input** — always visible below each exercise, appends sets on Enter/blur (never replaces). Understands:
  - `3x5` or `3×5` — 3 working sets of 5 reps
  - `3 sets of 5` — natural language form
  - `3x5@225` — 3 sets at 225 lbs
  - `3x5 at 65% 70% 75%` — 3 sets with per-set percentages
  - `65% 70% 75%` — bare weight/percent list → one set each
  - A count badge shows "N sets" above the input when sets exist; a "clear" button resets them
- 3 default sets per new exercise (not 5)
- Save button at bottom — no Cancel, no "Save as template" checkbox (simplified)
- **Post-save flow for future dates**: instead of redirecting to `/workouts`, shows an inline "Scheduled! Plan [next day] → · Done" status line. "Plan next day →" resets the form in-place for the following date — enables planning a full week without navigating away.

**AI button**: Opens AI slide-up sheet (see Domain 9)

**Key files**: `frontend/templates/log.html`, `backend/api/routes/workouts.py`, `backend/api/routes/exercises.py`

**Save flow**: POST `/api/workouts/` → for each exercise POST `/api/workouts/<id>/exercises` → redirect to `/workouts` (or inline plan-next-day flow for future dates)

**Future ideas**: Repeat last workout shortcut, date quick-pills (+1 through +7 days), bulk week planning from log page

---

### Domain 3 — Live Session (`/session/<workout_id>`)

**What it does**: The during-workout experience. Started from a template or opened from workout history. Shows exercises and sets, lets you tick off sets in real-time.

**UX design**:
- Minimal header: back arrow | workout title | status badge | unit toggle
- No bottom nav (intentional — a session is a focused mode)
- Each exercise block shows: name | TM badge (if set) | `done/total` progress counter
- When all sets in a block are complete: green left border + green name (`.all-done`)
- **Tap the circle** → instant toggle `completed` (no sheet, one tap) → **auto-starts rest timer**
- **Tap the rest of the row** → opens edit sheet (to adjust reps/weight/% before or after doing the set)
- Edit sheet: set type pills | reps | weight | `% of TM` → `weight ↔ %` bidirectional sync | last-session hint | Cancel | Save
- **Rest timer bar** (above action bar): 60/90/120/180s presets, countdown, vibrates on finish; last preset persisted in `localStorage`
- **Last-session hint**: edit sheet fetches `GET /api/exercises/last-session?name=` and shows e.g. "Last: 5×185 lbs · 5×195 lbs (Apr 2)"
- **Split-tap onboarding hint**: dismissible overlay on first session load; stored in `localStorage.split_tap_hint_seen`
- Fixed bottom bar: `+ Add Exercise` | `Complete Workout`
- Unit preference injected via `{{ unit }}` Jinja variable — restores correct unit on page load

**Elapsed timer**: Shown in the action bar between the two buttons. Start time stored in `sessionStorage` under `session_elapsed_start_<workout_id>`. Only active for non-completed sessions. Persists across page refreshes.

**Key files**: `frontend/templates/session.html`, `backend/api/routes/exercises.py` (`PATCH /api/session-sets/<id>`, `GET /api/exercises/last-session`), `backend/api/routes/workouts.py` (`POST /api/workouts/<id>/complete`)

**Future ideas**: Superset grouping, session notes, program progress indicator ("Week 2 / Day 3")

---

### Domain 4 — Workout History (`/workouts`)

**What it does**: Chronological list of all logged and completed workouts. Entry point to view or re-open any past session.

**Search**: A search bar above the calendar filters `allWorkouts` by title client-side. Typing hides the calendar and shows a flat list; clearing restores the calendar. Clicking a result navigates to `/session/<id>`.

**Key files**: `frontend/templates/workouts.html`, `backend/api/routes/workouts.py`

**API**: `GET /api/workouts/?page=<n>&limit=<n>` returns a paginated response `{workouts, total, page, pages, has_next}`. Omit `page=` for backwards-compatible full list. `DELETE /api/workouts/<id>` cascades to exercises and sets. The calendar in `workouts.html` fetches all pages sequentially on load.

**Future ideas**: Filter by exercise, weekly/monthly grouping headers, export to CSV

---

### Domain 5 — Templates (`/templates`)

**What it does**: Build reusable workout templates with exercises, sets, reps, and percentages. Start a workout from a template to create a planned session.

**UX design**:
- Search bar at top filters by name, description, or exercise name (client-side)
- Single-column list of cards: name + exercise preview | Start | Edit | ×
- **Start** goes directly to today's session — no date modal (one tap to go)
- Edit opens a builder modal with full exercise + set editing
- Builder supports: exercise autocomplete from library, set type, reps, `weight_lb`, `% of TM`

**Template → Session flow**:
1. `POST /api/templates/<id>/start` with `{date}` → calls `template_service.create_session_from_template()`
2. Service creates a `Workout` with `status="planned"` and deep-copies all exercises + sets
3. Returns the new `Workout` object → frontend redirects to `/session/<workout_id>`

**Key models**: `WorkoutTemplate`, `WorkoutTemplateExercise`, `WorkoutTemplateSet`
**Key files**: `frontend/templates/templates.html`, `backend/api/routes/templates.py`, `backend/services/template_service.py`

**Seeding templates**: `scripts/seed_ppsa_templates.py` restores 42 PPSA templates (22 Squatober 2023 + 20 70s Big days) via the live API. Run after seeding the DB if templates are lost.

**Template persistence**: `seed.py` updates the admin user in-place (never deletes+recreates) so `user_id` stays stable and templates are never orphaned.

**Future ideas**: Template categories/tags, share/import via JSON, template duplication

---

### Domain 5b — Programs (`/programs`)

**What it does**: Organizes templates into a named training cycle (e.g. "5/3/1 Wave 1") with a weekly schedule. Each week contains ordered days; each day optionally references a template. Hitting "Start" on a day creates a live session from that template.

**Models**: `Program` → `ProgramDay` (see Data Models)

**UX — `/programs`**:
- List all programs with week count, day count, and start date
- Create / edit modal: name, total weeks, description
- Delete confirmation modal
- Bottom nav Programs tab (active)

**UX — `/programs/<id>`**:
- View mode: weekly schedule grouped by `week_number`, each day shows label + template name + **Start** button
- **Edit Schedule** button (navbar) toggles inline editor:
  - Per-week sections with add/remove week controls
  - Per-day rows: label input + template dropdown (`— Rest day —` = no template)
  - Add Day / Remove Day per week
  - **Save Schedule** sends `PUT /api/programs/<id>` with full `days` array (replaces all)
  - Cancel returns to view without saving
- Start session modal: date picker → `POST /api/programs/<id>/days/<day_id>/start` → redirects to `/session/<id>`

**API**:
- `GET /api/programs/` — list with `include_days=True`
- `POST /api/programs/` — `{name, total_weeks, description?, days?}`
- `GET /api/programs/<id>` — single with days
- `PUT /api/programs/<id>` — full update including `days` replacement
- `DELETE /api/programs/<id>` — cascade deletes days
- `POST /api/programs/<id>/days/<day_id>/start` — `{date?}` → creates session, returns Workout

**Key files**: `frontend/templates/programs.html`, `frontend/templates/program_detail.html`, `backend/api/routes/programs.py`, `backend/services/program_service.py`, `backend/models/program.py`

**Future ideas**: Auto-advance to next session after completing one, program progress indicator on session page, duplicate program

---

### Domain 6 — Exercise Library

**What it does**: A global catalogue of named exercises with categories. Used for autocomplete everywhere, training max linkage, and template building.

**Model**: `ExerciseLibrary` — `id`, `name` (unique), `category`, `is_active`

**API**: `GET /api/library/` returns all active exercises. The response is cached in `_libraryCache` in `main.js` after the first fetch (via `attachLibraryAutocomplete`).

**Autocomplete**: `attachLibraryAutocomplete(inputEl, listEl, onSelectCallback)` in `main.js` handles fuzzy search and dropdown rendering. Used on log, session, templates, and maxes pages.

**Key files**: `backend/api/routes/library.py`, `backend/models/exercise_library.py`, `frontend/static/js/main.js`

**Future ideas**: Admin UI to add/edit library exercises, user-defined custom exercises, exercise categories filter, muscle group tagging, movement pattern tagging

---

### Domain 7 — Training Maxes & Percentage Programming (`/maxes`)

**What it does**: The user manually sets a **Training Max (TM)** per exercise. This is the weight used as the base for all percentage-based programming (e.g. 5/3/1, PPSA, Squatober). It is **never auto-overwritten** by logged performance — the user controls it.

**Key concept**: TM ≠ 1RM. In most programs, TM is set conservatively (e.g. 90% of true 1RM) to leave room for AMRAP sets.

**UX**:
- `/maxes` page: table of all TMs with edit/delete
- On the log page: when an exercise is linked to the library and has a TM, a `TM: X lbs` badge appears above the sets, and a `%` column appears in each set row
- Typing a `%` → weight auto-calculates: `round(TM × % / 100 / 2.5) × 2.5`
- Typing a `weight` → % auto-calculates: `round(weight / TM × 100)`
- Each set has its own independent `%` — progressive sets (e.g. 55%, 65%, 75%, 1+@85%) are the intended workflow
- The `percent` value is stored on the `ExerciseSet` record at save time

**Key models**: `TrainingMax` (unique per user+exercise library entry)
**Key files**: `frontend/templates/maxes.html`, `backend/api/routes/training_maxes.py`, `backend/services/training_max_service.py`

**API**:
- `GET /api/training-maxes/` — list all TMs for current user
- `POST /api/training-maxes/` — `{exercise_id, training_max_weight, notes?}` → upsert
- `DELETE /api/training-maxes/<id>` → delete

**Future ideas**: TM progression suggestions (e.g. "your squat TM is due for a 5 lb increase based on last 3 sessions"), TM history log, import TMs from a previous program

---

### Domain 8 — Personal Records

**What it does**: Automatically tracks the best weight ever logged per exercise. Used on the dashboard "Best Recorded Lifts" card.

**Two separate mechanisms**:

1. **PersonalMax table** (`/api/maxes/`): Tracks best lift per exercise *name string*. Auto-updated by `exercise_service._auto_update_max()` whenever a set is saved. Manual maxes (`is_manual=True`) are never overwritten. Visible on the old maxes dashboard section (removed from dashboard, still in DB).

2. **Stats endpoint live query** (`/api/stats` → `personal_records`): Computes top 10 exercises by `MAX(weight_lb)` directly from the `exercise_sets` table at query time. These are what the dashboard shows. No separate storage needed.

**Key files**: `backend/models/personal_max.py`, `backend/services/max_service.py`, `backend/api/routes/stats.py`

**Future ideas**: PR history over time (chart), PR alerts during session ("That's a new PR!"), categorized PRs (e.g. per movement pattern)

---

### Domain 9 — AI Workout Builder

**What it does**: Generates personalized workout suggestions based on a user prompt, training history, active training maxes, and AI memory. The user can accept and load the suggestion into the workout builder, or save it as a template.

**Entry point**: The `✦ AI` pill button in the log page meta strip opens a slide-up bottom sheet.

**Sheet flow**:
1. User types an optional prompt (e.g. "Heavy leg day" or "Upper body, 45 min, no bench")
2. Tap "Suggest Workout" → POST `/api/ai/suggest` with `{prompt}`
3. Loading skeleton displays while waiting
4. Result renders: workout name + goal → exercise list with set blocks → action buttons
5. Action buttons:
   - **Use This Workout** (primary): loads exercises into the log builder, closes sheet
   - **Save Template**: saves as a reusable template via `POST /api/ai/save-template`
   - **Regenerate**: re-calls suggest (limited by `ui_max_regens` Jinja variable)
   - Collapsible "AI noticed" section shows any observations the AI made
6. The AI can also respond in "answer mode" for questions (e.g. "what's a good warm-up?")

**AI memory**: The AI reads `AIKnowledge` records when building context. It writes new observations after accepting a workout. Admins can manage memory at `/ai-memory`.

**Cost controls**: `ai_config.py` contains `MAX_REGENS_PER_SESSION` and other rate limits. The `ui_max_regens` Jinja variable passes this to the frontend — preserve the `{{ ui_max_regens }}` expression in `log.html`.

**Key files**: `frontend/templates/log.html` (AI sheet UI), `backend/api/routes/ai_trainer.py`, `backend/services/ai_trainer_service.py`, `backend/models/ai_knowledge.py`, `backend/ai_config.py`

**API**:
- `POST /api/ai/title` — `{exercises:[names], weekday?}` → `{title}` (cheap: ~10 output tokens via `complete_mini`)
- `POST /api/ai/suggest` — `{prompt?}` → AI response object
- `POST /api/ai/accept` — `{ai_result, date?}` → saves workout + exercises to DB
- `POST /api/ai/save-template` — `{ai_result}` → saves as WorkoutTemplate
- `GET /api/ai/memory` — list AI knowledge records (admin)
- `DELETE /api/ai/memory/<id>` → delete record
- `PATCH /api/ai/memory/<id>` → toggle active/inactive

**Future ideas**: AI context from recent session performance, TM update suggestions, program adherence tracking, weekly planning suggestions

---

### Domain 10 — Stats & Dashboard (`/dashboard`)

**What it does**: Overview of training activity. Loads a single `/api/stats` call that returns everything.

**Stats returned**:
- `total_workouts`, `total_minutes`, `this_week`, `current_streak` — shown as stat cards
- `personal_records` — top 10 exercises by max weight_lb (live query, see Domain 8)
- `top_exercises` — top 8 most-logged exercises by name (bar chart)
- `daily_activity` — array of `{date, count}` for last 84 days (12 weeks) for activity heatmap

**UX**: 4 stat cards → Best Recorded Lifts table → Most Logged Exercises bars → Activity heatmap

**Key files**: `frontend/templates/dashboard.html`, `backend/api/routes/stats.py`

**Future ideas**: Progress charts per exercise over time, volume tracking (sets × reps × weight), training load trends, comparison vs. previous month

---

### Domain 11 — Navigation & UX System

**Design principles**:
- **Workout-first**: during a session, every tap should be purposeful; no decisions that don't matter in the moment
- **Progressive disclosure**: complexity (AI, percentages, set types) only appears when relevant
- **Mobile-first ergonomics**: all interactive targets are thumb-sized; no horizontal scroll

**Navigation**:
- **Top navbar**: logo + unit toggle + sign-out icon only. Nav links are hidden (`.nav-links { display: none }`).
- **Bottom tab bar** (`.bottom-nav`): Log | History | Templates | **Programs** | Stats. Fixed at 60px (`--bn-height`). Safe-area inset support for iPhone home indicator. Active tab detected via `request.path` in `_bottom_nav.html` (Jinja2 — Flask injects `request` globally).
- **Session page** intentionally has no bottom nav — sessions are a focused mode with their own action bar.
- `.container` has `padding-bottom: calc(var(--bn-height) + 1.5rem)` so content never hides behind the nav.

**Unit toggle**: `lbs ↔ kg` toggle. `initUnitToggle(onChangeCallback)` in `main.js` handles rendering; on toggle it calls `PATCH /api/users/me` to persist server-side. On login, `data.user.unit` is written to `localStorage`. Session page injects `{{ unit }}` into `localStorage` via a `<script>` tag before `main.js` loads. All weight display uses `displayWeight()` / `toDisplayWeight()` and all weight input uses `fromInputWeight()`.

**CSS architecture**: All styles in `frontend/static/css/main.css`. Uses CSS custom properties (design tokens) defined in `:root`. Key tokens: `--accent`, `--bg`, `--surface`, `--surface-2`, `--surface-3`, `--border`, `--border-strong`, `--rule`, `--text`, `--text-2`, `--text-muted`, `--radius` (8px), `--radius-lg` (12px), `--bn-height` (60px), `--font-display`, `--font-body`. Motion tokens: `--dur-fast` (120ms), `--dur` (180ms), `--dur-slow` (260ms), `--ease`, `--ease-out`. Global `border-radius` is 8px.

**Modal system**: All modals use an opacity/pointer-events toggle — **not** `display:none`. To open: add `.open` class. To close: remove `.open`. Never toggle `.hidden` on overlays. Use `openModal(id)` / `closeModal(id)` and `openSheet(id)` / `closeSheet(id)` helpers from `main.js`. Background click to close is wired by `openModal` automatically.

**Micro-interactions**: iOS Safari `:active` fix — a single passive `touchstart` listener on `document` (top of `main.js`) enables CSS `:active` states for the whole app. `prefers-reduced-motion` media query reduces all animation durations to `0.01ms`. `:focus-visible` provides keyboard-only focus rings (no outline on touch).

**Shared JS** (`main.js`):
- `api(path, method, body)` — fetch wrapper with JWT auth and error handling
- `attachLibraryAutocomplete(input, list, onSelect)` — exercise search dropdown, caches library in `_libraryCache`
- `displayWeight(lbs)` / `toDisplayWeight(lbs)` / `fromInputWeight(val)` — unit conversion
- `unitLabel()` / `weightInputStep()` — context-aware unit strings
- `initUnitToggle(onChange)` — sets up unit toggle button; persists to server via `PATCH /api/users/me`
- `escapeHtml(str)` — XSS-safe string rendering
- `formatDate(iso)` — human-readable date
- `initLogout()` — wires `#logout-btn` click; safe to call when button is absent
- `showToast(message, type, duration)` — creates/auto-dismisses toast; type: `"success" | "error" | "info"`
- `openModal(id)` / `closeModal(id)` — toggle `.open` class; `openModal` adds backdrop-click-to-close
- `openSheet(id)` / `closeSheet(id)` — toggle `.open` class on bottom sheets
- `confirmInline(cellEl, onConfirm, message, onCancel)` — replaces cell content with inline Yes/No confirm prompt

**Key files**: `frontend/static/css/main.css`, `frontend/static/js/main.js`

---

## Full API Surface

### Auth
| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/api/users/register` | `{username, email, password}` | user object; sets auth cookie |
| POST | `/api/users/login` | `{username, password}` | user object; sets auth cookie |
| POST | `/api/users/logout` | — | clears auth cookie |
| GET | `/api/users/me` | — | `{id, username, email, unit}` |
| PATCH | `/api/users/me` | `{unit?}` | updated user object |

### Workouts
| Method | Path | Notes |
|---|---|---|
| GET | `/api/workouts/` | All workouts, date desc |
| POST | `/api/workouts/` | `{title, date?, notes?, duration_minutes?}` |
| GET | `/api/workouts/<id>` | Single workout |
| PUT | `/api/workouts/<id>` | Update title/notes/duration |
| DELETE | `/api/workouts/<id>` | Cascades to exercises + sets |
| POST | `/api/workouts/<id>/complete` | Sets `status="completed"` |
| POST | `/api/workouts/<id>/copy` | Duplicates workout |
| POST | `/api/workouts/<id>/save-as-template` | `{name}` → creates WorkoutTemplate |

### Exercises & Sets
| Method | Path | Notes |
|---|---|---|
| GET | `/api/workouts/<id>/exercises` | Exercise list with sets |
| POST | `/api/workouts/<id>/exercises` | `{name, exercise_library_id?, notes?, sets:[]}` |
| PUT | `/api/exercises/<id>` | Full set replacement |
| DELETE | `/api/exercises/<id>` | Cascades to sets |
| PATCH | `/api/session-sets/<id>` | `{reps?, weight_lb?, percent?, set_type?, completed?}` — used during live sessions |
| GET | `/api/exercises/last-session?name=<name>` | Most recent completed sets for an exercise: `{date, sets:[]}` |
| GET | `/api/exercises/history?name=<name>` | All completed sessions for an exercise (last 60): `{exercise, sessions:[{date, workout_id, workout_title, sets:[]}]}` |

### Exercise Library
| Method | Path | Notes |
|---|---|---|
| GET | `/api/library/` | All active exercises with category |

### Templates
| Method | Path | Notes |
|---|---|---|
| GET | `/api/templates/` | All templates with exercises+sets |
| POST | `/api/templates/` | `{name, description?, exercises:[]}` |
| GET | `/api/templates/<id>` | Single template |
| PUT | `/api/templates/<id>` | Full replace |
| DELETE | `/api/templates/<id>` | Cascade |
| POST | `/api/templates/<id>/start` | `{date}` → creates Workout + returns it |

### Training Maxes
| Method | Path | Notes |
|---|---|---|
| GET | `/api/training-maxes/` | All TMs for current user |
| POST | `/api/training-maxes/` | `{exercise_id, training_max_weight, notes?}` → upsert |
| DELETE | `/api/training-maxes/<id>` | Delete |

### Personal Maxes
| Method | Path | Notes |
|---|---|---|
| GET | `/api/maxes/` | All personal maxes |
| POST | `/api/maxes/` | `{exercise_name, weight_lb}` → upsert, always manual |
| DELETE | `/api/maxes/<id>` | Delete |

### Stats
| Method | Path | Notes |
|---|---|---|
| GET | `/api/stats` | Full dashboard stats object |

### Programs
| Method | Path | Notes |
|---|---|---|
| GET | `/api/programs/` | All programs with days |
| POST | `/api/programs/` | `{name, total_weeks?, description?, days?}` |
| GET | `/api/programs/<id>` | Single program with days |
| PUT | `/api/programs/<id>` | Full update; `days` key replaces all ProgramDays |
| DELETE | `/api/programs/<id>` | Cascade deletes days |
| POST | `/api/programs/<id>/days/<day_id>/start` | `{date?}` → creates session from day's template, returns Workout |

### AI Trainer
| Method | Path | Notes |
|---|---|---|
| POST | `/api/ai/title` | `{exercises:[names], weekday?}` → `{title}` (cheap title generation, ~10 tokens) |
| POST | `/api/ai/suggest` | `{prompt?}` → workout or answer object |
| POST | `/api/ai/accept` | `{ai_result, date?}` → saves workout |
| POST | `/api/ai/save-template` | `{ai_result}` → saves template |
| GET | `/api/ai/memory` | List AIKnowledge records |
| DELETE | `/api/ai/memory/<id>` | Delete record |
| PATCH | `/api/ai/memory/<id>` | Toggle active |

---

## Design System

Full design context lives in `.impeccable.md` at the project root. Always read that file before doing UI work. Summary below.

### Brand Identity
A complete brand identity handoff was received and applied (2026-05-03). The source files live at `~/Downloads/design_handoff_barpath_identity/` — `README.md` is the spec, `design_files/colors_and_type.css` is the canonical token file, `assets/barpath_stencil_b.svg` is the icon mark.

### Target Audience
Serious athletes, coaches, and gym-goers — many accustomed to paper training logs, not necessarily tech-savvy. Must work one-handed in a gym under harsh lighting. Also used by coaches reviewing athlete data at a desk.

### Brand Personality
**Disciplined, warm, industrial — gym-chalk and iron.** The physical analog is a programming sheet and equipment-grade documentation. Not Silicon Valley fitness; not glossy gradient bro-tech.

### References
- **Linear** — precision tool, dark, fast, zero decoration
- **Stripe** — typographic confidence, clear hierarchy, earns trust

### Anti-references
MyFitnessPal (noisy, consumer-y), Strong app (rough), Apple Fitness (lifestyle marketing). No motivational language, no achievement badges, no emoji.

### Theme
**Dark (Iron) by default.** Gym use, glare, chalk hands. Color system uses OKLCH throughout — all neutrals tinted toward **hue 60 (warm iron/forge)**, not cool steel/blue.

### Logo & Marks

**Icon mark — The Stencil B**: Capital B in Big Shoulders Display Black (weight 900), with two horizontal stencil cuts sliced through it (plate-edge slots). Construction grid: 320 × 320 units. Cut 1: y=118→132 (14u). Cut 2: y=208→222 (14u). SVG uses `fill="currentColor"` + `mask`. Pre-built SVG at `assets/barpath_stencil_b.svg`. Each inline use must have a **unique `mask id`** (e.g. `bp-cuts-nav`, `bp-cuts-log`) to avoid SVG mask collisions across pages.

**Wordmark**: "BARPATH" as live HTML text — Big Shoulders Display 900, `letter-spacing: 0.02em`, `text-transform: uppercase`. Never use the old path-drawn SVG wordmark.

**Size rules**:
- Navbar: mark at 28px + wordmark at 1rem
- Hero / auth: mark at 40–72px + wordmark at clamp or fixed size
- Below 16px: drop cuts, use solid B

**Do not**: rotate, stretch, outline, gradient-fill, or drop-shadow the mark. Ember is never used as the Stencil B fill.

### Typography

| Tier | Family | Weight | Size | Line-height | Tracking | Case |
|---|---|---|---|---|---|---|
| Display | Big Shoulders Display | 900 | 96px | 0.88 | +0.005em | UPPER |
| H1 | Big Shoulders Display | 800 | 56px | 0.92 | +0.005em | UPPER |
| H2 | Big Shoulders Display | 800 | 36px | 0.95 | +0.01em | UPPER |
| H3 | Big Shoulders Display | 700 | 22px | 1.05 | +0.02em | UPPER |
| Eyebrow | Big Shoulders Display | 900 | 12px | 1 | +0.28em | UPPER — always Ember |
| Body | IBM Plex Mono | 400 | 16px | 1.55 | −0.005em | sentence |
| Meta | IBM Plex Mono | 500 | 13px | 1.5 | 0 | sentence |
| Data | IBM Plex Mono | 600 | 14px | 1.4 | +0.02em | UPPER — often Ember |

Google Fonts import:
```
https://fonts.googleapis.com/css2?family=Big+Shoulders+Display:wght@700;800;900&family=IBM+Plex+Mono:wght@400;500;600;700&display=swap
```

**Important**: `colors_and_type.css` in the handoff bundle ships `--bp-font-body: 'Hanken Grotesk'` — this is a known error in that file. The correct body font is IBM Plex Mono. The app's `main.css` uses the correct value.

CSS classes: `.eyebrow` is defined in `main.css`. Use it for all section labels, card eyebrows, and categorical labels (currently `.home-section-label`, `.wh-label`, `.acct-section-title`, `.dash-card-title` are candidates for migration).

### Color System

**OKLCH is the source of truth.** Three primaries, two signals.

| Name | OKLCH (dark) | Role |
|---|---|---|
| Iron | `oklch(8% 0.005 60)` | Default surface / page bg |
| Bone | `oklch(95% 0.010 85)` | Primary text on dark |
| Ember | `oklch(70% 0.175 42)` | The single accent — CTAs, rules, highlights |
| PR Green | `oklch(72% 0.19 142)` | Personal record / success (product UI only) |
| Heavy Red | `oklch(50% 0.22 22)` | Overload / failure / destructive (product UI only) |

**Surface ramp (dark/Iron):**
```
--bg:           oklch(8%  0.005 60)   /* page background */
--surface:      oklch(12% 0.006 60)   /* card / panel */
--surface-2:    oklch(16% 0.007 60)   /* input / inset */
--surface-3:    oklch(20% 0.008 60)   /* pressed / hover */
--border:       oklch(28% 0.010 60)   /* hairline */
--border-strong:oklch(32% 0.010 60)   /* emphasized hairline */
--rule:         oklch(14% 0.006 60)   /* paper-ruled bg line */
```

**Text:**
```
--text:         oklch(95% 0.010 85)   /* primary, warm bone */
--text-2:       oklch(74% 0.010 75)   /* secondary */
--text-muted:   oklch(48% 0.012 70)   /* tertiary */
```

**Accent (Ember):**
```
--accent:       oklch(70% 0.175 42)
--accent-hover: oklch(65% 0.175 42)
--accent-dim:   oklch(70% 0.175 42 / .12)
--accent-dim-2: oklch(70% 0.175 42 / .22)
--on-accent:    oklch(14% 0.020 40)   /* Iron on Ember */
```

**Signals (product UI only — never marketing):**
```
--success / --pr:  oklch(62% 0.17 145) / oklch(72% 0.19 142)
--danger / --heavy:oklch(58% 0.20 14)  / oklch(50% 0.22 22)
```

**Set-type badge colors:**
```
--set-warmup:  oklch(76% 0.13 85)    /* wheat */
--set-working: oklch(72% 0.16 148)   /* olive-green */
--set-amrap:   oklch(70% 0.175 42)   /* ember */
--set-emom:    oklch(60% 0.16 20)    /* terracotta */
--set-failure: oklch(56% 0.20 18)    /* oxblood */
```

**Color rules:**
- Ember is the **only** accent. No other accent colors.
- Never use Ember as the Stencil B fill (mark fill is always Bone on Iron, or Iron on Bone).
- Iron hue is 60 — warm charcoal. Never drift to neutral grey or blue.
- PR Green / Heavy Red never appear in marketing — product UI only.

### Motion Tokens
```
--dur-fast: 120ms   --ease:     cubic-bezier(.22, .68, 0, 1.08)
--dur:      180ms   --ease-out: cubic-bezier(.22, 1, .36, 1)
--dur-slow: 260ms
```

### Design Principles
1. **Friction is the enemy.** Mid-workout interactions must be one gesture.
2. **The data is the design.** Numbers are the product; typography serves them.
3. **Analog clarity.** As easy to read as a well-organized paper notebook.
4. **Earn trust quietly.** No cute empty states, no flickering skeletons. Fast and direct.
5. **Nothing without purpose.** If removing it doesn't change the experience, it shouldn't be there.

### Hard Rules
- No gradient text (`background-clip: text` with gradient fill — banned)
- No `border-left/right > 1px` as a colored accent stripe on cards or list items
- No glassmorphism used decoratively
- No generic card grids (icon + heading + text, repeated)
- No centered layout by default — left-aligned feels more designed

### CSS Architecture Notes
- All design tokens in `frontend/static/css/main.css` `:root` block, unprefixed (`--accent`, `--bg`, etc.). The handoff bundle uses `--bp-` prefix — when porting new tokens from the bundle, drop the prefix and add to `:root`.
- Token rename to `--bp-` prefix is a future task (tracked in ROADMAP Phase 7 #35).
- `login.html`, `log.html`, and `session.html` are standalone pages with inline `<style>` blocks — font imports and any token overrides must be kept in sync manually with `main.css`.

### Pages — Logo & Font Status
All 9 navbar surfaces now use the Stencil B + BARPATH wordmark consistently.

| Page | Navbar source | Status |
|---|---|---|
| `workouts.html`, `dashboard.html`, `account.html` | `_navbar.html` via `_base.html` | ✅ Stencil B + BARPATH |
| `log.html` | Inline nav | ✅ Stencil B + BARPATH |
| `exercise_history.html` | Inline nav | ✅ Stencil B + BARPATH |
| `templates.html` | Inline nav | ✅ Stencil B + BARPATH |
| `programs.html` | Inline nav | ✅ Stencil B + BARPATH |
| `program_detail.html` | Inline nav | ✅ Stencil B + BARPATH |
| `maxes.html` | Inline nav | ✅ Stencil B + BARPATH |
| `ai_memory.html` | Inline nav | ✅ Stencil B + BARPATH |

---

## Design Principles (Maintain These)

1. **No frontend framework.** Vanilla JS/HTML/CSS. No React, Vue, etc.
2. **No cloud dependencies.** Everything runs locally. The only external call is the Anthropic API for AI features.
3. **SQLite is fine.** Do not migrate to PostgreSQL without a concrete reason.
4. **Service layer holds business logic.** Route handlers validate input and delegate. Logic lives in `services/`.
5. **JWT in HttpOnly cookies.** Set via `set_access_cookies()`, cleared via `unset_jwt_cookies()`. `JWT_COOKIE_SECURE=True` in production (gated on `FLASK_ENV`). Don't change cookie config without understanding the CSRF implications (`JWT_COOKIE_CSRF_PROTECT=False` — SameSite=Strict handles it).
   **Security headers** are added on every response via `after_request` in `app.py`: `Content-Security-Policy` (unsafe-inline for scripts/styles — all templates use inline `<script>`), `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`.
6. **One file per model, one file per route group.**
7. **Workout-first UX.** New UI should reduce decisions during a session, not add them.
8. **Progressive disclosure.** Advanced features (TM %, AI, set types) only appear when contextually relevant.
9. **Template ID stability.** `seed.py` must never delete+recreate the admin user. Always update in-place.

---

## What the App Does Not Have (Yet)

- No body weight or cardio-specific logging mode
- No superset / circuit grouping
- No export (CSV, JSON)
- No refresh tokens (30-day access token used instead)
- No account settings or password change
- No multi-user admin tools
- No mobile native app (web only, but responsive and mobile-optimized)
- No auto-advance to next program session after completing one
- No program progress indicator on the session page
