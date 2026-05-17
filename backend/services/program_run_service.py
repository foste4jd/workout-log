import json
from datetime import datetime, timezone, timedelta, date as date_type

from backend.db.database import db
from backend.models.program import Program, ProgramDay, ProgramRun
from backend.models.workout import Workout
from backend.models.exercise import Exercise
from backend.models.exercise_set import ExerciseSet


def start_program(program_id, user_id, start_date_str, training_days):
    """Create a ProgramRun and generate all planned workout sessions."""
    program = Program.query.filter_by(id=program_id, user_id=user_id).first()
    if not program:
        return None, "Program not found"

    existing = get_active_run(user_id)
    if existing:
        return None, "You already have an active program. Cancel it before starting a new one."

    try:
        start_date = date_type.fromisoformat(start_date_str)
    except (ValueError, TypeError):
        return None, "Invalid start date"

    if not training_days or not isinstance(training_days, list):
        return None, "training_days must be a non-empty list of weekday numbers (1=Mon, 7=Sun)"

    try:
        days_sorted = sorted(set(int(d) for d in training_days if 1 <= int(d) <= 7))
    except (ValueError, TypeError):
        return None, "Invalid training_days values"

    if not days_sorted:
        return None, "No valid training days provided"

    run = ProgramRun(
        program_id=program.id,
        user_id=user_id,
        start_date=start_date,
        training_days=json.dumps(days_sorted),
        status="active",
    )
    db.session.add(run)
    db.session.flush()

    dates = _schedule_dates(start_date, days_sorted, program.total_weeks)
    sorted_days = sorted(program.days, key=lambda d: (d.week_number, d.day_order))

    for i, day in enumerate(sorted_days):
        if i >= len(dates):
            break
        _create_planned_workout(run, day, user_id, dates[i])

    db.session.commit()
    return run, None


def cancel_run(run_id, user_id):
    run = ProgramRun.query.filter_by(id=run_id, user_id=user_id, status="active").first()
    if not run:
        return None, "Active run not found"

    Workout.query.filter_by(program_run_id=run.id, status="planned").delete()
    run.status = "cancelled"
    db.session.commit()
    return run, None


def complete_run(run_id, user_id):
    run = ProgramRun.query.filter_by(id=run_id, user_id=user_id, status="active").first()
    if not run:
        return None, "Active run not found"
    run.status = "completed"
    db.session.commit()
    return run, None


def get_active_run(user_id):
    return ProgramRun.query.filter_by(user_id=user_id, status="active").first()


def get_run_workouts(run_id, user_id):
    """Return all workouts for a run, keyed by program_day_id."""
    workouts = Workout.query.filter_by(program_run_id=run_id, user_id=user_id).all()
    return {w.program_day_id: w for w in workouts}


def duplicate_program(program_id, user_id):
    program = Program.query.filter_by(id=program_id, user_id=user_id).first()
    if not program:
        return None

    new_prog = Program(
        user_id=user_id,
        name=f"{program.name} (copy)",
        description=program.description,
        total_weeks=program.total_weeks,
    )
    db.session.add(new_prog)
    db.session.flush()

    for day in program.days:
        db.session.add(ProgramDay(
            program_id=new_prog.id,
            week_number=day.week_number,
            day_order=day.day_order,
            template_id=day.template_id,
            label=day.label,
        ))

    db.session.commit()
    return new_prog


def _schedule_dates(start_date, training_days_of_week, total_weeks):
    """Return ordered list of training dates for total_weeks starting from start_date."""
    current = start_date
    # Advance to first selected weekday >= start_date
    while current.isoweekday() not in training_days_of_week:
        current += timedelta(days=1)

    end_date = current + timedelta(weeks=total_weeks)
    dates = []
    d = current
    while d < end_date:
        if d.isoweekday() in training_days_of_week:
            dates.append(d)
        d += timedelta(days=1)
    return dates


def _create_planned_workout(run, day, user_id, scheduled_date):
    from backend.models.workout_template import WorkoutTemplate

    template = WorkoutTemplate.query.get(day.template_id) if day.template_id else None
    title = (template.name if template else None) or day.label or f"Day {day.day_order}"

    workout = Workout(
        user_id=user_id,
        title=title,
        status="planned",
        template_id=day.template_id,
        date=datetime.combine(scheduled_date, datetime.min.time()).replace(tzinfo=timezone.utc),
        program_run_id=run.id,
        program_day_id=day.id,
    )
    db.session.add(workout)
    db.session.flush()

    if template:
        for te in sorted(template.exercises, key=lambda x: x.order_index):
            ex = Exercise(
                workout_id=workout.id,
                exercise_library_id=te.exercise_id,
                name=te.exercise.name,
                notes=te.notes,
            )
            db.session.add(ex)
            db.session.flush()
            for ts in sorted(te.sets, key=lambda x: x.set_number):
                db.session.add(ExerciseSet(
                    exercise_id=ex.id,
                    set_number=ts.set_number,
                    set_type=ts.set_type or "working",
                    planned_reps=ts.reps,
                    planned_weight_lb=ts.weight_lb,
                    planned_percent=ts.percent,
                    duration_seconds=ts.duration_seconds,
                    completed=False,
                ))
