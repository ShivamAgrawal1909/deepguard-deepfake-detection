import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "deepfake-detection-secret-key-2024")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'deepfake_detection.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    DATASET_FOLDER = os.path.join(BASE_DIR, "dataset")
    MODEL_FOLDER = os.path.join(BASE_DIR, "models")
    REPORT_FOLDER = os.path.join(BASE_DIR, "reports")
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB
    ALLOWED_VIDEO_EXTENSIONS = {"mp4", "avi", "mov", "mkv", "webm"}
    ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "bmp", "webp"}
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)
    DEFAULT_FRAME_COUNT = 16
    DEFAULT_FRAME_SIZE = 224
    DEFAULT_FFT_BANDS = 8
    DEFAULT_TRANSFORMER_LAYERS = 4
    DEFAULT_TRANSFORMER_HEADS = 4
    DEFAULT_EMBED_DIM = 128
