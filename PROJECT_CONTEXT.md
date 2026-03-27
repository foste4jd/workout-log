# WorkoutLog — Project Context for AI Assistance

Use this document to give an AI assistant full context about this project when asking for feature ideas, implementation help, or code improvements.

---

## What This App Is

WorkoutLog is a personal workout tracking web app. It is a single-user-per-account tool where each user logs their own training sessions, tracks exercises with sets/reps/weight, monitors personal bests, and views a stats dashboard. It is not a social app — there is no sharing, following, or public profiles.

The app is intentionally simple and lightweight. It is not a SaaS product, does not use a cloud database, and has no payment system. The goal is a clean, fast, self-hosted tool for tracking strength training progress.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.13 |
| Web framework | Flask (app factory pattern) |
| ORM | SQLAlchemy (via Flask-SQLAlchemy) |
| Auth | Flask-JWT-Extended (JWT tokens stored in localStorage) |
| Password hashing | Flask-Bcrypt |
| Database | SQLite (single file, `workout_log.db`) |
| Frontend | Vanilla HTML, CSS, JavaScript (no framework, no build step) |
| Templates | Jinja2 (server renders the HTML shell; JS fetches data from the API) |

There are no external services, no message queues, no caching layer, and no third-party APIs. Everything runs locally from `python -m backend.app`.

---

## Project Structure

```
workout-log/
├── backend/
│   ├── app.py                  # App factory (create_app), blueprint registration
│   ├── config.py               # Config class (reads from .env)
│   ├── db/
│   │   └── database.py         # SQLAlchemy db instance
│   ├── models/
│   │   ├── user.py             # User model
│   │   ├── workout.py          # Workout model
│   │   ├── exercise.py         # Exercise model (belongs to a workout)
│   │   ├── exercise_set.py     # ExerciseSet model (belongs to an exercise)
│   │   └── personal_max.py     # PersonalMax model (1RM per exercise per user)
│   ├── services/
│   │   ├── workout_service.py  # CRUD for workouts
│   │   ├── exercise_service.py # CRUD for exercises + sets + auto-max logic
│   │   └── max_service.py      # CRUD for personal maxes
│   └── api/routes/
│       ├── users.py            # POST /api/users/register, POST /api/users/login
│       ├── workouts.py         # GET/POST/PUT/DELETE /api/workouts/
│       ├── exercises.py        # GET/POST /api/workouts/<id>/exercises, PUT/DELETE /api/exercises/<id>
│       ├── maxes.py            # GET/POST /api/maxes/, DELETE /api/maxes/<id>
│       ├── stats.py            # GET /api/stats
│       └── views.py            # Page routes (render Jinja2 templates)
├── frontend/
│   ├── templates/
│   │   ├── index.html          # Landing/home page
│   │   ├── login.html          # Login and register forms
│   │   ├── workouts.html       # List of past workouts
│   │   ├── log.html            # Form to log a new workout
│   │   ├── dashboard.html      # Stats dashboard
│   │   └── maxes.html          # Personal maxes management
│   └── static/
│       └── css/
│           └── main.css        # Dark-themed responsive stylesheet
├── seed.py                     # Populates DB with a demo account and sample workouts
└── requirements.txt
```

---

## Data Models

### User
- `id`, `username` (unique), `email` (unique), `password_hash`
- Has many `Workout`s

### Workout
- `id`, `user_id`, `title`, `notes`, `duration_minutes`, `date`
- Has many `Exercise`s (cascade delete)
- `date` defaults to UTC now but can be set manually (supports back-logging)

### Exercise
- `id`, `workout_id`, `name`, `notes`
- Has many `ExerciseSet`s (cascade delete, ordered by `set_number`)
- Belongs to one `Workout`

### ExerciseSet
- `id`, `exercise_id`, `set_number`, `reps`, `weight_lb`
- Represents a single set within an exercise
- `reps` and `weight_lb` are both nullable (supports bodyweight or cardio)

### PersonalMax
- `id`, `user_id`, `exercise_name`, `weight_lb`, `is_manual`
- Unique constraint on `(user_id, exercise_name)` — one record per exercise per user
- `is_manual=True` means the user set it explicitly on the maxes page; the system will never auto-overwrite a manual max
- `is_manual=False` means it was automatically recorded when an exercise set was saved

---

## Key Business Logic

### Auto-Max Tracking
When an exercise is created or updated via the API, `exercise_service._auto_update_max()` runs automatically. It finds the highest `weight_lb` across all sets in that exercise. If no personal max exists for that exercise name, it creates one (`is_manual=False`). If one exists and it is not manual, it updates it if the new weight is higher. Manual maxes are never touched by this logic.

### Stats Endpoint (`GET /api/stats`)
Returns a single JSON object with:
- `total_workouts` — all-time count
- `total_minutes` — sum of all `duration_minutes`
- `this_week` — workouts since Monday of the current week
- `this_month` — workouts since the 1st of the current month
- `current_streak` — consecutive days with at least one workout, counting back from today (or yesterday if no workout today)
- `personal_records` — top 10 exercises by max `weight_lb` across all sets, derived live from exercise data (not from the `PersonalMax` table)
- `top_exercises` — top 8 most frequently logged exercises by name
- `daily_activity` — array of `{date, count}` for the last 84 days (12 weeks), used for an activity heatmap

### Authentication Flow
- Register: POST username, email, password → user created, password bcrypt-hashed
- Login: POST email, password → returns a JWT access token
- All protected routes require `Authorization: Bearer <token>` header
- JWT identity is `str(user.id)`; routes parse it with `int(get_jwt_identity())`
- Tokens are stored in `localStorage` on the frontend and attached to API calls via JavaScript fetch

---

## Pages and Their Purpose

| Route | Template | Description |
|---|---|---|
| `/` | `index.html` | Landing page / home |
| `/login` | `login.html` | Login and registration forms |
| `/workouts` | `workouts.html` | Lists all past workouts with delete/edit |
| `/log` | `log.html` | Form to create a new workout with exercises and sets |
| `/dashboard` | `dashboard.html` | Stats: streak, weekly/monthly counts, top exercises, heatmap, PRs |
| `/maxes` | `maxes.html` | View and manually manage personal maxes |

All pages are server-rendered shells. The actual data is loaded client-side via `fetch()` calls to the JSON API using the JWT from localStorage.

---

## API Surface

### Auth (no token required)
- `POST /api/users/register` — `{username, email, password}`
- `POST /api/users/login` — `{email, password}` → `{access_token}`

### Workouts (token required)
- `GET /api/workouts/` — list all workouts for the current user
- `POST /api/workouts/` — `{title, notes?, duration_minutes?, date?}` → create
- `GET /api/workouts/<id>` — fetch one
- `PUT /api/workouts/<id>` — `{title?, notes?, duration_minutes?}` → update
- `DELETE /api/workouts/<id>` → delete (cascades to exercises and sets)

### Exercises (token required)
- `GET /api/workouts/<id>/exercises` — list exercises for a workout
- `POST /api/workouts/<id>/exercises` — `{name, notes?, sets: [{reps?, weight_lb?}]}` → create exercise with sets; triggers auto-max update
- `PUT /api/exercises/<id>` — `{name?, notes?, sets?}` → full set replacement if sets provided; triggers auto-max update
- `DELETE /api/exercises/<id>` → delete exercise and its sets

### Personal Maxes (token required)
- `GET /api/maxes/` — list all personal maxes, ordered by exercise name
- `POST /api/maxes/` — `{exercise_name, weight_lb}` → upsert; always sets `is_manual=True`
- `DELETE /api/maxes/<id>` → delete

### Stats (token required)
- `GET /api/stats` → full stats object (see Key Business Logic above)

---

## What the App Does NOT Have (yet)

This list is intentionally honest — it represents real gaps that could be features:

- No workout templates or programs (e.g., save a StrongLifts A/B template and reuse it)
- No exercise library or autocomplete (exercise names are free-text strings; "Squat" and "squat" are treated as different exercises in stats)
- No unit toggle — weights are always in lbs; no kg support
- No body weight or cardio-specific logging (though `weight_lb` and `reps` are nullable)
- No progress charts or graphs (the stats endpoint returns raw data but there is no charting UI)
- No pagination on the workouts list
- No search or filter on the workouts list
- No edit-in-place on the workout detail view
- No workout duration timer
- No mobile app — web only, though the CSS is responsive
- No export (CSV, JSON backup, etc.)
- No account settings or password change
- No multi-user admin tools
- No rate limiting on the API
- No refresh token — JWT expires and the user must log in again

---

## Design Principles to Maintain

When suggesting improvements, keep these constraints in mind:

1. **No frontend framework.** The frontend is intentionally vanilla JS/HTML/CSS. Avoid suggesting React, Vue, or similar unless the task clearly requires it.
2. **No cloud dependencies.** Everything should work locally with no external services.
3. **SQLite is fine.** Do not suggest migrating to PostgreSQL unless there is a concrete reason.
4. **Keep the service layer thin.** Business logic lives in `services/`, not in route handlers.
5. **JWT in localStorage.** This is a known tradeoff (vs. httpOnly cookies). Accept it unless security hardening is the explicit goal.
6. **One file per model, one file per route group.** Maintain the existing file organization pattern.
