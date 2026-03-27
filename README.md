# WorkoutLog

A simple web app to log and track your workouts.

## Stack

- **Backend:** Python, Flask, SQLAlchemy, Flask-JWT-Extended
- **Frontend:** Vanilla HTML, CSS, JavaScript
- **Database:** SQLite

## Features

- User registration and login with JWT authentication
- Log workouts with a title, duration, and notes
- View, edit, and delete past workouts
- Track exercises with sets, reps, and weight per workout
- Log and manage personal maxes (1RM) per exercise
- Dashboard with workout stats: streaks, weekly/monthly counts, top exercises, activity heatmap, and personal records
- Responsive dark-themed UI

## Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/foste4jd/workout-log.git
cd workout-log
```

### 2. Create a virtual environment and install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and set secure values for `SECRET_KEY` and `JWT_SECRET_KEY`.

### 4. Seed sample data (optional)

```bash
python seed.py
```

This creates a demo account:
- **Email:** demo@example.com
- **Password:** password123

### 5. Run the server

```bash
python -m backend.app
```

Open http://localhost:5000 in your browser.

## API Endpoints

All authenticated requests require an `Authorization: Bearer <token>` header.

### Auth

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/users/register` | No | Register a new user |
| POST | `/api/users/login` | No | Login, returns JWT token |

### Workouts

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/workouts/` | Yes | List your workouts |
| POST | `/api/workouts/` | Yes | Log a new workout |
| GET | `/api/workouts/<id>` | Yes | Get a single workout |
| PUT | `/api/workouts/<id>` | Yes | Update a workout |
| DELETE | `/api/workouts/<id>` | Yes | Delete a workout |

### Exercises

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/workouts/<id>/exercises` | Yes | List exercises for a workout |
| POST | `/api/workouts/<id>/exercises` | Yes | Add an exercise to a workout |
| PUT | `/api/exercises/<id>` | Yes | Update an exercise |
| DELETE | `/api/exercises/<id>` | Yes | Delete an exercise |

### Personal Maxes

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/maxes/` | Yes | List your personal maxes |
| POST | `/api/maxes/` | Yes | Create or update a personal max |
| DELETE | `/api/maxes/<id>` | Yes | Delete a personal max |

### Stats

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/stats` | Yes | Get workout stats and personal records |

The stats endpoint returns total workouts, total minutes, this week/month counts, current streak, top exercises by frequency, personal records by weight, and daily activity for the last 12 weeks.

## Project Structure

```
workout-log/
├── backend/
│   ├── app.py              # App factory and entry point
│   ├── config.py           # Configuration
│   ├── api/routes/         # Route handlers
│   │   ├── users.py        # Auth routes
│   │   ├── workouts.py     # Workout CRUD
│   │   ├── exercises.py    # Exercise CRUD
│   │   ├── maxes.py        # Personal maxes
│   │   ├── stats.py        # Stats and analytics
│   │   └── views.py        # Page rendering
│   ├── models/             # SQLAlchemy models
│   │   ├── user.py
│   │   ├── workout.py
│   │   ├── exercise.py
│   │   ├── exercise_set.py # Sets with reps and weight
│   │   └── personal_max.py # Per-exercise 1RM records
│   ├── services/           # Business logic
│   └── db/                 # Database setup
├── frontend/
│   ├── templates/          # HTML pages
│   │   ├── index.html      # Landing page
│   │   ├── login.html      # Login/register
│   │   ├── workouts.html   # Workout list
│   │   ├── log.html        # Log a workout
│   │   ├── dashboard.html  # Stats dashboard
│   │   └── maxes.html      # Personal maxes
│   └── static/             # CSS and JavaScript
├── seed.py                 # Sample data script
└── requirements.txt
```