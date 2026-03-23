import os
from flask import Flask
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from backend.config import Config
from backend.db.database import db

bcrypt = Bcrypt()
jwt = JWTManager()

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(ROOT_DIR, "frontend", "templates"),
        static_folder=os.path.join(ROOT_DIR, "frontend", "static"),
    )
    app.config.from_object(Config)

    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)

    from backend.api.routes.users import users_bp
    from backend.api.routes.workouts import workouts_bp
    from backend.api.routes.exercises import exercises_bp
    from backend.api.routes.views import views_bp
    app.register_blueprint(users_bp)
    app.register_blueprint(workouts_bp)
    app.register_blueprint(exercises_bp)
    app.register_blueprint(views_bp)

    with app.app_context():
        db.create_all()

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=8080)
