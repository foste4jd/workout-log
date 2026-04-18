# WorkoutLog

A self-hosted strength training tracker. Log workouts, run percentage-based programs, track personal records, and get AI-generated workout suggestions — all from a clean, mobile-first web UI.

---

## Features

### Workout Logging
- Log any workout after the fact: title, date, duration, notes
- Add exercises with sets, reps, and weight
- Each set has a type (working, warmup, AMRAP, EMOM, failure) — tap to cycle, no dropdown
- Per-set percentage of training max with bidirectional weight ↔ % sync

### Live Sessions
- Start a session from a template and tick off sets in real time
- Tap the circle to instantly mark a set done — no modal, no friction
- Tap the rest of the row to edit reps, weight, or % before/after completing
- Last-session weight/reps hint shown inline when editing a set ("Last: 5×185 lbs")
- Rest timer auto-starts on set completion — 60/90/120/180s presets, vibrates when done
- First-use onboarding hint explains the split-tap interaction
- Per-exercise progress counter (e.g. 2/5 sets done); green border when all complete
- Complete the workout with a single button

### Templates & Programs
- Build reusable templates with named exercises, set schemes, and percentages
- Full set-level detail: type, reps, weight, % of TM
- One-tap "Start" from the template list — goes straight to today's session
- Search templates by name or exercise
- Save any logged workout as a template
- Includes a script to bulk-seed PPSA programs (Squatober 2023, 70s Big)

### Percentage-Based Programming
- Set a Training Max (TM) per exercise — manually controlled, never auto-overwritten
- TM badge appears above sets whenever a linked exercise has a max
- Type a % → weight calculates automatically (rounded to nearest 2.5)
- Type a weight → % calculates automatically
- Each set has its own independent %, enabling progressive set schemes (55% / 65% / 75% / 1+@85%)

### AI Workout Builder
- Tap the AI button in the log page to open a slide-up suggestion sheet
- Type an optional prompt or leave blank for a context-aware suggestion
- AI considers training history, active training maxes, and stored user preferences
- Accept → exercises load directly into the workout builder
- Save as template for future reuse
- Regenerate with a limit (configurable in `ai_config.py`)
- AI memory system: stores observations about training patterns, schedule, injuries

### Personal Records & Stats
- Auto-tracks best weight per exercise across all logged sets
- Dashboard: total workouts, hours trained, this week count, day streak
- Best recorded lifts table (top 10 by weight)
- Most logged exercises (bar chart)
- Activity heatmap — last 12 weeks

### Exercise Library
- Shared catalogue of 150+ exercises with categories
- Powers autocomplete on every exercise input across the app
- Links exercises to training maxes and templates

### UX
- Mobile-first dark UI — designed to be used in a gym
- Bottom tab bar: Log | History | Templates | Profile
- Unit toggle: lbs ↔ kg — persisted server-side, restored across devices on login
- No framework, no build step — plain HTML/CSS/JS

---

## Getting Started

### 1. Clone and install

```bash
git clone https://github.com/foste4jd/workout-log.git
cd workout-log
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret
ANTHROPIC_API_KEY=your-key-here   # Optional — only needed for AI features
```

### 3. Seed sample data

```bash
python seed.py
```

Creates a demo account: `admin` / `password`

To also seed the 42 PPSA workout templates:

```bash
python scripts/seed_ppsa_templates.py
```

### 4. Run

```bash
python -m backend.app
```

Open [http://localhost:8080](http://localhost:8080)

---

## Pages

| Route | Description |
|---|---|
| `/` | Landing page |
| `/login` | Login / register |
| `/log` | Log a new workout |
| `/session/<id>` | Live workout session |
| `/workouts` | Workout history |
| `/templates` | Template library + builder |
| `/maxes` | Training max management |
| `/dashboard` | Stats, PRs, heatmap |
| `/ai-memory` | AI knowledge admin |

---

## API Summary

Authentication uses `HttpOnly SameSite=Strict` cookies — no `Authorization` header required. All protected endpoints are cookie-authenticated.

### Auth
```
POST  /api/users/register    {username, email, password} → sets auth cookie
POST  /api/users/login       {username, password} → sets auth cookie
POST  /api/users/logout      clears auth cookie
GET   /api/users/me          current user object {id, username, email, unit}
PATCH /api/users/me          {unit: "lb"|"kg"} → update preferences
```

### Workouts
```
GET    /api/workouts/?page=<n>&limit=<n>   paginated; omit page= for all
POST   /api/workouts/                       {title, date?, notes?, duration_minutes?}
GET    /api/workouts/<id>
PUT    /api/workouts/<id>
DELETE /api/workouts/<id>
POST   /api/workouts/<id>/complete
POST   /api/workouts/<id>/copy
POST   /api/workouts/<id>/save-as-template  {name}
```

### Exercises & Sets
```
GET    /api/workouts/<id>/exercises
POST   /api/workouts/<id>/exercises    {name, exercise_library_id?, notes?, sets:[]}
PUT    /api/exercises/<id>             full set replacement
DELETE /api/exercises/<id>
PATCH  /api/session-sets/<id>          {reps?, weight_lb?, percent?, set_type?, completed?}
GET    /api/exercises/last-session?name=<name>   most recent completed sets for an exercise
```

### Library
```
GET /api/library/
```

### Templates
```
GET    /api/templates/
POST   /api/templates/              {name, description?, exercises:[]}
PUT    /api/templates/<id>
DELETE /api/templates/<id>
POST   /api/templates/<id>/start    {date} → creates Workout, returns it
```

### Training Maxes
```
GET    /api/training-maxes/
POST   /api/training-maxes/         {exercise_id, training_max_weight, notes?}
DELETE /api/training-maxes/<id>
```

### Stats
```
GET /api/stats    → {total_workouts, total_minutes, this_week, current_streak,
                     personal_records, top_exercises, daily_activity}
```

### AI
```
POST /api/ai/suggest          {prompt?} → workout or answer object
POST /api/ai/accept           {ai_result, date?} → saves workout
POST /api/ai/save-template    {ai_result} → saves template
GET  /api/ai/memory
DELETE /api/ai/memory/<id>
PATCH  /api/ai/memory/<id>    toggle active
```

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.13, Flask, SQLAlchemy |
| Auth | Flask-JWT-Extended |
| Database | SQLite |
| Frontend | Vanilla HTML / CSS / JavaScript |
| AI | Anthropic Claude API |

---

## Project Structure

```
workout-log/
├── backend/
│   ├── app.py                  # App factory, blueprint registration
│   ├── config.py               # Config (reads .env)
│   ├── ai_config.py            # AI feature flags and cost controls
│   ├── models/                 # SQLAlchemy models
│   │   ├── user.py
│   │   ├── workout.py
│   │   ├── exercise.py
│   │   ├── exercise_set.py     # set_type, percent, completed, duration_seconds
│   │   ├── exercise_library.py # Global exercise catalogue
│   │   ├── workout_template.py # Template + Exercise + Set (3 tables)
│   │   ├── training_max.py     # TM per user per exercise
│   │   ├── personal_max.py     # Auto-tracked best lift by name
│   │   └── ai_knowledge.py     # AI memory records
│   ├── services/               # Business logic
│   │   ├── workout_service.py
│   │   ├── exercise_service.py
│   │   ├── template_service.py
│   │   ├── training_max_service.py
│   │   ├── max_service.py
│   │   └── ai_trainer_service.py
│   └── api/routes/             # Route handlers
│       ├── users.py
│       ├── workouts.py
│       ├── exercises.py
│       ├── library.py
│       ├── templates.py
│       ├── training_maxes.py
│       ├── maxes.py
│       ├── stats.py
│       ├── ai_trainer.py
│       └── views.py
├── frontend/
│   ├── templates/              # HTML pages (Jinja2)
│   │   ├── log.html            # Log workout
│   │   ├── session.html        # Live session
│   │   ├── workouts.html       # History
│   │   ├── templates.html      # Templates
│   │   ├── maxes.html          # Training maxes
│   │   └── dashboard.html      # Stats
│   └── static/
│       ├── css/main.css        # All styles + design tokens
│       └── js/main.js          # api(), unit toggle, autocomplete, helpers
├── scripts/
│   └── seed_ppsa_templates.py  # Bulk seed 42 PPSA templates via API
└── seed.py                     # Demo account + sample data
```
