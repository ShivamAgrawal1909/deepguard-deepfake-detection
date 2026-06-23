import json
import os
import uuid
from datetime import datetime

from flask import current_app, request
from werkzeug.utils import secure_filename

from app import db
from app.models import (
    DetectionHistory,
    LoginHistory,
    SystemLog,
    SystemSetting,
    UploadHistory,
)


def allowed_file(filename, file_type="video"):
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    if file_type == "video":
        return ext in current_app.config["ALLOWED_VIDEO_EXTENSIONS"]
    if file_type == "image":
        return ext in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]
    return ext in current_app.config["ALLOWED_VIDEO_EXTENSIONS"] | current_app.config[
        "ALLOWED_IMAGE_EXTENSIONS"
    ]


def save_upload(file, subfolder="videos"):
    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    folder = os.path.join(current_app.config["UPLOAD_FOLDER"], subfolder)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, filename)
    file.save(path)
    return filename, path


def get_setting(key, default=None):
    setting = SystemSetting.query.filter_by(key=key).first()
    if setting:
        try:
            return json.loads(setting.value)
        except (json.JSONDecodeError, TypeError):
            return setting.value
    return default


def set_setting(key, value, category="general"):
    serialized = json.dumps(value) if not isinstance(value, str) else value
    setting = SystemSetting.query.filter_by(key=key).first()
    if setting:
        setting.value = serialized
        setting.category = category
    else:
        setting = SystemSetting(key=key, value=serialized, category=category)
        db.session.add(setting)
    db.session.commit()


def ensure_default_settings():
    defaults = {
        "frame_extraction": {
            "frame_count": current_app.config["DEFAULT_FRAME_COUNT"],
            "frame_size": current_app.config["DEFAULT_FRAME_SIZE"],
            "face_detection": True,
        },
        "frequency_processing": {
            "fft_bands": current_app.config["DEFAULT_FFT_BANDS"],
            "noise_threshold": 0.35,
            "texture_sensitivity": 0.5,
        },
        "transformer_model": {
            "layers": current_app.config["DEFAULT_TRANSFORMER_LAYERS"],
            "heads": current_app.config["DEFAULT_TRANSFORMER_HEADS"],
            "embed_dim": current_app.config["DEFAULT_EMBED_DIM"],
            "dropout": 0.1,
        },
    }
    for key, value in defaults.items():
        if not SystemSetting.query.filter_by(key=key).first():
            set_setting(key, value, category=key.split("_")[0])


def log_action(log_type, action, details=None, user_id=None):
    entry = SystemLog(
        log_type=log_type,
        action=action,
        details=details,
        user_id=user_id,
        ip_address=request.remote_addr if request else None,
    )
    db.session.add(entry)
    db.session.commit()


def log_login(user, status="success"):
    entry = LoginHistory(
        user_id=user.id if user else None,
        username=user.username if user else "unknown",
        role=user.role if user else None,
        ip_address=request.remote_addr if request else None,
        status=status,
    )
    db.session.add(entry)
    db.session.commit()


def log_upload(user_id, filename, file_type, file_size, status="success"):
    entry = UploadHistory(
        user_id=user_id,
        filename=filename,
        file_type=file_type,
        file_size=file_size,
        status=status,
    )
    db.session.add(entry)
    db.session.commit()


def log_detection_history(detection):
    entry = DetectionHistory(
        detection_id=detection.id,
        user_id=detection.user_id,
        result_label=detection.result_label,
        confidence=detection.confidence,
        status=detection.status,
    )
    db.session.add(entry)
    db.session.commit()


def format_datetime(dt):
    if not dt:
        return "-"
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def paginate_query(query, page=1, per_page=10):
    return query.paginate(page=page, per_page=per_page, error_out=False)
