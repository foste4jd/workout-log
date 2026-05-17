from backend.db.database import db
from backend.models.program import Program, ProgramDay


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
    )
    db.session.add(program)
    db.session.flush()
    _replace_days(program, data.get("days", []))
    db.session.commit()
    return program


def update_program(program, data):
    from backend.models.program import ProgramRun
    if "days" in data or "total_weeks" in data:
        active = ProgramRun.query.filter_by(
            program_id=program.id, status="active"
        ).first()
        if active:
            return None, "Cannot edit a program with an active run. Cancel the run first."

    program.name = data.get("name", program.name)
    program.description = data.get("description", program.description)
    program.total_weeks = data.get("total_weeks", program.total_weeks)
    if "days" in data:
        for day in list(program.days):
            db.session.delete(day)
        db.session.flush()
        _replace_days(program, data["days"])
    db.session.commit()
    return program, None


def delete_program(program):
    db.session.delete(program)
    db.session.commit()



def _replace_days(program, days_data):
    for d in days_data:
        db.session.add(ProgramDay(
            program_id=program.id,
            week_number=d.get("week_number", 1),
            day_order=d.get("day_order", 1),
            template_id=d.get("template_id"),
            label=d.get("label"),
        ))


