import os
from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    for folder in [
        app.config["UPLOAD_FOLDER"],
        app.config["DATASET_FOLDER"],
        app.config["MODEL_FOLDER"],
        app.config["REPORT_FOLDER"],
        os.path.join(app.config["DATASET_FOLDER"], "real"),
        os.path.join(app.config["DATASET_FOLDER"], "fake"),
    ]:
        os.makedirs(folder, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.admin import admin_bp
    from app.routes.user import user_bp
    from app.routes.detection import detection_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(user_bp, url_prefix="/user")
    app.register_blueprint(detection_bp, url_prefix="/detection")

    with app.app_context():
        db.create_all()
        from app.utils.helpers import ensure_default_settings

        ensure_default_settings()

    return app
