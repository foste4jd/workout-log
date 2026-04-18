from datetime import datetime, timezone
from backend.db.database import db
from backend.models.program import Program, ProgramDay
from backend.models.workout_template import WorkoutTemplate


def get_programs(user_id):
    return (
        Program.query
        .filter_by(user_id=user_id)
        .order_by(Program.name)
        .all()
    )


def get_program(program_id, user_id):
    return Program.query.filter_by(id=program_id, user_id=user_id).first()


def create_program(user_id, data):
    program = Program(
        user_id=user_id,
        name=data["name"],
        description=data.get("description"),
        total_weeks=data.get("total_weeks", 4),
        start_date=_parse_date(data.get("start_date")),
    )
    db.session.add(program)
    db.session.flush()
    _replace_days(program, data.get("days", []))
    db.session.commit()
    return program


def update_program(program, data):
    program.name = data.get("name", program.name)
    program.description = data.get("description", program.description)
    program.total_weeks = data.get("total_weeks", program.total_weeks)
    if "start_date" in data:
        program.start_date = _parse_date(data["start_date"])
    if "days" in data:
        for day in list(program.days):
            db.session.delete(day)
        db.session.flush()
        _replace_days(program, data["days"])
    db.session.commit()
    return program


def delete_program(program):
    db.session.delete(program)
    db.session.commit()


def start_program_day(program, day_id, user_id, date=None):
    """Start a specific program day by creating a session from its template."""
    from backend.services import template_service
    day = ProgramDay.query.filter_by(id=day_id, program_id=program.id).first()
    if not day or not day.template_id:
        return None
    template = WorkoutTemplate.query.filter_by(id=day.template_id, user_id=user_id).first()
    if not template:
        return None
    return template_service.create_session_from_template(template, user_id, date)


def _replace_days(program, days_data):
    for d in days_data:
        db.session.add(ProgramDay(
            program_id=program.id,
            week_number=d.get("week_number", 1),
            day_order=d.get("day_order", 1),
            template_id=d.get("template_id"),
            label=d.get("label"),
        ))


def _parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str)
    except (ValueError, TypeError):
        return None
