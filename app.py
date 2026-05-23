"""
app.py — Flask application factory for SIWES Placement Portal
Run:    flask run  OR  python app.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from flask_login import LoginManager
from database import init_db, SessionLocal
from models import User

# ── Upload folder ──────────────────────────────────────
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "siwes-dev-secret-2024")
    app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024   # 5 MB CV limit

    # ── Database ──────────────────────────────────────
    init_db()

    # ── Flask-Login ───────────────────────────────────
    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "warning"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        db = SessionLocal()
        try:
            return db.query(User).get(int(user_id))
        finally:
            db.close()

    # ── Blueprints ────────────────────────────────────
    from blueprints.auth      import auth_bp
    from blueprints.student   import student_bp
    from blueprints.admin     import admin_bp
    from blueprints.placement import placement_bp
    from blueprints.schools   import schools_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp,   url_prefix="/student")
    app.register_blueprint(admin_bp,     url_prefix="/admin")
    app.register_blueprint(placement_bp, url_prefix="/placement")
    app.register_blueprint(schools_bp,   url_prefix="/schools")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)
