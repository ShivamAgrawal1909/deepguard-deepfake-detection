import json
import os
from datetime import datetime

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user
from werkzeug.utils import secure_filename

from app import db
from app.models import ContactQuery, DetectionRequest, Feedback, Video, VideoCategory
from app.services.detection_service import DetectionService
from app.services.video_processor import VideoProcessor
from app.utils.decorators import user_required
from app.utils.helpers import allowed_file, log_action, log_upload, paginate_query, save_upload

user_bp = Blueprint("user", __name__)


@user_bp.app_context_processor
def inject_now():
    return {"now": datetime.utcnow}


@user_bp.route("/dashboard")
@user_required
def dashboard():
    uid = current_user.id
    stats = {
        "uploads": Video.query.filter_by(user_id=uid).count(),
        "detections": DetectionRequest.query.filter_by(user_id=uid).count(),
        "completed": DetectionRequest.query.filter_by(user_id=uid, status="completed").count(),
        "pending": DetectionRequest.query.filter_by(user_id=uid, status="pending").count(),
        "failed": DetectionRequest.query.filter_by(user_id=uid, status="failed").count(),
        "real": DetectionRequest.query.filter_by(user_id=uid, result_label="real").count(),
        "fake": DetectionRequest.query.filter_by(user_id=uid, result_label="fake").count(),
    }
    recent = DetectionRequest.query.filter_by(user_id=uid).order_by(
        DetectionRequest.created_at.desc()
    ).limit(8).all()
    videos = Video.query.filter_by(user_id=uid).order_by(Video.created_at.desc()).limit(5).all()
    return render_template("user/dashboard.html", stats=stats, recent=recent, videos=videos)


@user_bp.route("/videos")
@user_required
def my_videos():
    page = request.args.get("page", 1, type=int)
    pagination = paginate_query(
        Video.query.filter_by(user_id=current_user.id).order_by(Video.created_at.desc()), page
    )
    return render_template("user/my_videos.html", pagination=pagination)


@user_bp.route("/profile", methods=["GET", "POST"])
@user_required
def profile():
    if request.method == "POST":
        current_user.full_name = request.form.get("full_name", "")
        current_user.email = request.form.get("email", "")
        current_user.phone = request.form.get("phone", "")
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("user.profile"))
    return render_template("user/profile.html")


@user_bp.route("/change-password", methods=["GET", "POST"])
@user_required
def change_password():
    if request.method == "POST":
        if not current_user.check_password(request.form.get("current_password", "")):
            flash("Current password incorrect.", "danger")
        elif request.form.get("new_password") != request.form.get("confirm_password"):
            flash("Passwords do not match.", "danger")
        else:
            current_user.set_password(request.form.get("new_password"))
            db.session.commit()
            flash("Password changed.", "success")
            return redirect(url_for("user.profile"))
    return render_template("user/change_password.html")


@user_bp.route("/upload", methods=["GET", "POST"])
@user_required
def upload_video():
    categories = VideoCategory.query.order_by(VideoCategory.name).all()
    if request.method == "POST":
        file = request.files.get("video")
        title = request.form.get("title", "Untitled Video").strip()
        cat_id = request.form.get("category_id")

        if not file or not file.filename:
            flash("Please select a video file.", "danger")
        elif not allowed_file(file.filename, "video"):
            flash("Invalid format. Allowed: mp4, avi, mov, mkv, webm", "danger")
        else:
            filename, path = save_upload(file, "videos")
            processor = VideoProcessor()
            valid, info = processor.validate_video(path)
            if not valid:
                os.remove(path)
                flash(info, "danger")
                return render_template("user/upload.html", categories=categories)

            thumb_name = f"thumb_{filename.rsplit('.', 1)[0]}.jpg"
            thumb_path = os.path.join(current_app.config["UPLOAD_FOLDER"], "thumbnails", thumb_name)
            os.makedirs(os.path.dirname(thumb_path), exist_ok=True)
            processor.save_thumbnail(path, thumb_path)

            ext = file.filename.rsplit(".", 1)[1].lower()
            video = Video(
                user_id=current_user.id,
                category_id=int(cat_id) if cat_id else None,
                title=title,
                filename=filename,
                original_filename=secure_filename(file.filename),
                file_size=os.path.getsize(path),
                duration=info.get("duration", 0),
                format=ext,
                thumbnail=thumb_name,
                status="uploaded",
            )
            db.session.add(video)
            db.session.commit()
            log_upload(current_user.id, filename, "video", video.file_size)
            log_action("upload", "Video uploaded", title, current_user.id)
            flash("Video uploaded successfully.", "success")
            return redirect(url_for("user.video_preview", video_id=video.id))

    return render_template("user/upload.html", categories=categories)


@user_bp.route("/videos/<int:video_id>/preview")
@user_required
def video_preview(video_id):
    video = Video.query.filter_by(id=video_id, user_id=current_user.id).first_or_404()
    return render_template("user/video_preview.html", video=video)


@user_bp.route("/videos/<int:video_id>/detect", methods=["POST"])
@user_required
def submit_detection(video_id):
    video = Video.query.filter_by(id=video_id, user_id=current_user.id).first_or_404()
    detection = DetectionRequest(
        user_id=current_user.id,
        video_id=video.id,
        request_type="video",
        status="pending",
    )
    db.session.add(detection)
    db.session.commit()

    service = DetectionService()
    success, result = service.process_detection(detection.id)
    if success:
        flash("Detection completed successfully.", "success")
        return redirect(url_for("user.detection_result", det_id=detection.id))
    flash(f"Detection failed: {result}", "danger")
    return redirect(url_for("user.detection_result", det_id=detection.id))


@user_bp.route("/detect/image", methods=["GET", "POST"])
@user_required
def detect_image():
    if request.method == "POST":
        file = request.files.get("image")
        if not file or not allowed_file(file.filename, "image"):
            flash("Please upload a valid image (jpg, png, bmp, webp).", "danger")
        else:
            filename, path = save_upload(file, "images")
            detection = DetectionRequest(
                user_id=current_user.id,
                request_type="image",
                image_filename=filename,
                status="pending",
            )
            db.session.add(detection)
            db.session.commit()
            log_upload(current_user.id, filename, "image", os.path.getsize(path))

            service = DetectionService()
            success, result = service.process_detection(detection.id)
            if success:
                flash("Image analysis completed.", "success")
            else:
                flash(f"Analysis failed: {result}", "danger")
            return redirect(url_for("user.detection_result", det_id=detection.id))
    return render_template("user/detect_image.html")


@user_bp.route("/results/<int:det_id>")
@user_required
def detection_result(det_id):
    det = DetectionRequest.query.filter_by(id=det_id, user_id=current_user.id).first_or_404()
    frame_data = json.loads(det.frame_analysis) if det.frame_analysis else []
    freq_data = json.loads(det.frequency_analysis) if det.frequency_analysis else {}
    video = det.video if det.video_id else None
    return render_template(
        "user/detection_result.html",
        detection=det,
        frame_data=frame_data,
        freq_data=freq_data,
        video=video,
    )


@user_bp.route("/results/<int:det_id>/download")
@user_required
def download_report(det_id):
    det = DetectionRequest.query.filter_by(id=det_id, user_id=current_user.id).first_or_404()
    if det.report_path:
        path = os.path.join(current_app.config["REPORT_FOLDER"], det.report_path)
        if os.path.exists(path):
            return send_file(path, as_attachment=True)
    flash("Report not available.", "warning")
    return redirect(url_for("user.detection_result", det_id=det_id))


@user_bp.route("/history")
@user_required
def history():
    search = request.args.get("search", "")
    status = request.args.get("status", "")
    result = request.args.get("result", "")
    req_type = request.args.get("type", "")
    page = request.args.get("page", 1, type=int)
    query = DetectionRequest.query.filter_by(user_id=current_user.id)
    if search:
        query = query.filter(
            (DetectionRequest.result_label.contains(search))
            | (DetectionRequest.status.contains(search))
        )
    if status:
        query = query.filter_by(status=status)
    if result in ("real", "fake"):
        query = query.filter_by(result_label=result)
    if req_type in ("video", "image"):
        query = query.filter_by(request_type=req_type)
    pagination = paginate_query(query.order_by(DetectionRequest.created_at.desc()), page)
    return render_template(
        "user/history.html",
        pagination=pagination,
        search=search,
        status=status,
        result=result,
        req_type=req_type,
    )


@user_bp.route("/history/<int:det_id>/delete", methods=["POST"])
@user_required
def delete_history(det_id):
    det = DetectionRequest.query.filter_by(id=det_id, user_id=current_user.id).first_or_404()
    if det.report_path:
        path = os.path.join(current_app.config["REPORT_FOLDER"], det.report_path)
        if os.path.exists(path):
            os.remove(path)
    db.session.delete(det)
    db.session.commit()
    flash("Detection record deleted.", "success")
    return redirect(url_for("user.history"))


@user_bp.route("/feedback", methods=["GET", "POST"])
@user_required
def feedback():
    if request.method == "POST":
        subject = request.form.get("subject", "").strip()
        message = request.form.get("message", "").strip()
        if subject and message:
            item = Feedback(user_id=current_user.id, subject=subject, message=message)
            db.session.add(item)
            db.session.commit()
            flash("Feedback submitted. Thank you!", "success")
            return redirect(url_for("user.feedback"))
        flash("Subject and message are required.", "danger")
    items = Feedback.query.filter_by(user_id=current_user.id).order_by(
        Feedback.created_at.desc()
    ).all()
    return render_template("user/feedback.html", items=items)


@user_bp.route("/contact", methods=["GET", "POST"])
@user_required
def contact():
    if request.method == "POST":
        query = ContactQuery(
            name=request.form.get("name", current_user.full_name or current_user.username),
            email=request.form.get("email", current_user.email),
            subject=request.form.get("subject", ""),
            message=request.form.get("message", ""),
        )
        db.session.add(query)
        db.session.commit()
        flash("Your message has been sent.", "success")
        return redirect(url_for("user.contact"))
    return render_template("user/contact.html")
