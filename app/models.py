from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    role = db.Column(db.String(20), default="user")  # admin | user
    is_active_account = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    videos = db.relationship("Video", backref="owner", lazy=True)
    detections = db.relationship("DetectionRequest", backref="user", lazy=True)
    feedback_items = db.relationship("Feedback", backref="user", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == "admin"


class VideoCategory(db.Model):
    __tablename__ = "video_categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    videos = db.relationship("Video", backref="category", lazy=True)


class Video(db.Model):
    __tablename__ = "videos"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("video_categories.id"))
    title = db.Column(db.String(200), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255))
    file_size = db.Column(db.Integer)
    duration = db.Column(db.Float)
    format = db.Column(db.String(20))
    thumbnail = db.Column(db.String(255))
    status = db.Column(db.String(30), default="uploaded")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    detections = db.relationship("DetectionRequest", backref="video", lazy=True)


class DetectionRequest(db.Model):
    __tablename__ = "detection_requests"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey("videos.id"))
    request_type = db.Column(db.String(20), default="video")  # video | image
    image_filename = db.Column(db.String(255))
    status = db.Column(db.String(20), default="pending")  # pending | completed | failed
    result_label = db.Column(db.String(20))  # real | fake
    confidence = db.Column(db.Float)
    frame_analysis = db.Column(db.Text)
    frequency_analysis = db.Column(db.Text)
    summary = db.Column(db.Text)
    report_path = db.Column(db.String(255))
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)


class DatasetRecord(db.Model):
    __tablename__ = "dataset_records"

    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(10), nullable=False)  # real | fake
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255))
    file_size = db.Column(db.Integer)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SystemSetting(db.Model):
    __tablename__ = "system_settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ModelTraining(db.Model):
    __tablename__ = "model_training"

    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), default="idle")  # idle | training | completed | failed
    epochs = db.Column(db.Integer, default=10)
    current_epoch = db.Column(db.Integer, default=0)
    accuracy = db.Column(db.Float)
    loss = db.Column(db.Float)
    loss_history = db.Column(db.Text)
    accuracy_history = db.Column(db.Text)
    model_path = db.Column(db.String(255))
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    message = db.Column(db.Text)


class Feedback(db.Model):
    __tablename__ = "feedback"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="pending")  # pending | reviewed | resolved
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ContactQuery(db.Model):
    __tablename__ = "contact_queries"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    reply_status = db.Column(db.String(20), default="pending")  # pending | replied
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SystemLog(db.Model):
    __tablename__ = "system_logs"

    id = db.Column(db.Integer, primary_key=True)
    log_type = db.Column(db.String(50), nullable=False)
    action = db.Column(db.String(200), nullable=False)
    details = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class LoginHistory(db.Model):
    __tablename__ = "login_history"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    username = db.Column(db.String(80))
    role = db.Column(db.String(20))
    ip_address = db.Column(db.String(50))
    status = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class UploadHistory(db.Model):
    __tablename__ = "upload_history"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    filename = db.Column(db.String(255))
    file_type = db.Column(db.String(20))
    file_size = db.Column(db.Integer)
    status = db.Column(db.String(30))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class DetectionHistory(db.Model):
    __tablename__ = "detection_history"

    id = db.Column(db.Integer, primary_key=True)
    detection_id = db.Column(db.Integer, db.ForeignKey("detection_requests.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    result_label = db.Column(db.String(20))
    confidence = db.Column(db.Float)
    status = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
