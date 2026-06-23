import os

from flask import Blueprint, current_app, send_from_directory
from flask_login import login_required

detection_bp = Blueprint("detection", __name__)


@detection_bp.route("/uploads/<folder>/<filename>")
@login_required
def serve_upload(folder, filename):
    base = current_app.config["UPLOAD_FOLDER"]
    return send_from_directory(os.path.join(base, folder), filename)


@detection_bp.route("/thumbnails/<filename>")
@login_required
def serve_thumbnail(filename):
    return send_from_directory(
        os.path.join(current_app.config["UPLOAD_FOLDER"], "thumbnails"), filename
    )
