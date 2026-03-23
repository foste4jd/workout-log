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

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/users/register` | No | Register a new user |
| POST | `/api/users/login` | No | Login, returns JWT token |
| GET | `/api/workouts/` | Yes | List your workouts |
| POST | `/api/workouts/` | Yes | Log a new workout |
| GET | `/api/workouts/<id>` | Yes | Get a single workout |
| PUT | `/api/workouts/<id>` | Yes | Update a workout |
| DELETE | `/api/workouts/<id>` | Yes | Delete a workout |

Authenticated requests require an `Authorization: Bearer <token>` header.

## Project Structure

```
workout-log/
├── backend/
│   ├── app.py              # App factory and entry point
│   ├── config.py           # Configuration
│   ├── api/routes/         # Route handlers
│   ├── models/             # SQLAlchemy models
│   ├── services/           # Business logic
│   └── db/                 # Database setup
├── frontend/
│   ├── templates/          # HTML pages
│   └── static/             # CSS and JavaScript
├── seed.py                 # Sample data script
└── requirements.txt
```
