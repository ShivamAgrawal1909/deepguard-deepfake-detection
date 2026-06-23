import json
import os
import threading
from datetime import datetime, timedelta

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
from app.models import (
    ContactQuery,
    DatasetRecord,
    DetectionHistory,
    DetectionRequest,
    Feedback,
    LoginHistory,
    ModelTraining,
    SystemLog,
    UploadHistory,
    User,
    Video,
    VideoCategory,
)
from app.services.detection_service import DetectionService
from app.services.transformer_model import TransformerDetector
from app.utils.decorators import admin_required
from app.utils.helpers import (
    allowed_file,
    format_datetime,
    get_setting,
    log_action,
    paginate_query,
    save_upload,
    set_setting,
)

admin_bp = Blueprint("admin", __name__)


@admin_bp.app_context_processor
def inject_admin_globals():
    return {
        "now": datetime.utcnow,
        "admin_counts": {
            "pending_detections": DetectionRequest.query.filter_by(status="pending").count(),
            "pending_feedback": Feedback.query.filter_by(status="pending").count(),
            "pending_contacts": ContactQuery.query.filter_by(reply_status="pending").count(),
        },
    }


@admin_bp.route("/dashboard")
@admin_required
def dashboard():
    total_detections = DetectionRequest.query.count()
    stats = {
        "users": User.query.filter_by(role="user").count(),
        "active_users": User.query.filter_by(role="user", is_active_account=True).count(),
        "videos": Video.query.count(),
        "detections": total_detections,
        "pending": DetectionRequest.query.filter_by(status="pending").count(),
        "completed": DetectionRequest.query.filter_by(status="completed").count(),
        "failed": DetectionRequest.query.filter_by(status="failed").count(),
        "real": DetectionRequest.query.filter_by(result_label="real").count(),
        "fake": DetectionRequest.query.filter_by(result_label="fake").count(),
        "feedback": Feedback.query.filter_by(status="pending").count(),
        "contacts": ContactQuery.query.filter_by(reply_status="pending").count(),
        "dataset": DatasetRecord.query.count(),
        "categories": VideoCategory.query.count(),
    }
    recent_detections = DetectionRequest.query.order_by(DetectionRequest.created_at.desc()).limit(8).all()
    recent_logs = SystemLog.query.order_by(SystemLog.created_at.desc()).limit(10).all()
    recent_users = User.query.filter_by(role="user").order_by(User.created_at.desc()).limit(5).all()
    training = ModelTraining.query.order_by(ModelTraining.id.desc()).first()
    return render_template(
        "admin/dashboard.html",
        stats=stats,
        recent_detections=recent_detections,
        recent_logs=recent_logs,
        recent_users=recent_users,
        training=training,
    )


@admin_bp.route("/profile", methods=["GET", "POST"])
@admin_required
def profile():
    if request.method == "POST":
        current_user.full_name = request.form.get("full_name", "")
        current_user.email = request.form.get("email", "")
        current_user.phone = request.form.get("phone", "")
        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for("admin.profile"))
    return render_template("admin/profile.html")


@admin_bp.route("/change-password", methods=["GET", "POST"])
@admin_required
def change_password():
    if request.method == "POST":
        current_pw = request.form.get("current_password", "")
        new_pw = request.form.get("new_password", "")
        confirm = request.form.get("confirm_password", "")
        if not current_user.check_password(current_pw):
            flash("Current password is incorrect.", "danger")
        elif new_pw != confirm:
            flash("New passwords do not match.", "danger")
        elif len(new_pw) < 6:
            flash("Password must be at least 6 characters.", "danger")
        else:
            current_user.set_password(new_pw)
            db.session.commit()
            log_action("security", "Password changed", "Admin changed password", current_user.id)
            flash("Password changed successfully.", "success")
            return redirect(url_for("admin.profile"))
    return render_template("admin/change_password.html")


# --- Users ---
@admin_bp.route("/users")
@admin_required
def users():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "")
    status = request.args.get("status", "")
    query = User.query.filter_by(role="user")
    if search:
        query = query.filter(
            (User.username.contains(search)) | (User.email.contains(search))
        )
    if status == "active":
        query = query.filter_by(is_active_account=True)
    elif status == "inactive":
        query = query.filter_by(is_active_account=False)
    pagination = paginate_query(query.order_by(User.created_at.desc()), page)
    user_stats = {
        "total": User.query.filter_by(role="user").count(),
        "active": User.query.filter_by(role="user", is_active_account=True).count(),
        "inactive": User.query.filter_by(role="user", is_active_account=False).count(),
    }
    return render_template(
        "admin/users.html", pagination=pagination, search=search, status=status, user_stats=user_stats
    )


@admin_bp.route("/users/<int:user_id>")
@admin_required
def user_detail(user_id):
    user = db.session.get(User, user_id)
    if not user or user.is_admin:
        flash("User not found.", "danger")
        return redirect(url_for("admin.users"))
    detections = DetectionRequest.query.filter_by(user_id=user.id).order_by(
        DetectionRequest.created_at.desc()
    ).limit(10).all()
    videos = Video.query.filter_by(user_id=user.id).order_by(Video.created_at.desc()).limit(5).all()
    user_stats = {
        "detections": DetectionRequest.query.filter_by(user_id=user.id).count(),
        "videos": Video.query.filter_by(user_id=user.id).count(),
        "real": DetectionRequest.query.filter_by(user_id=user.id, result_label="real").count(),
        "fake": DetectionRequest.query.filter_by(user_id=user.id, result_label="fake").count(),
    }
    return render_template(
        "admin/user_detail.html", user=user, detections=detections, videos=videos, user_stats=user_stats
    )


@admin_bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@admin_required
def toggle_user(user_id):
    user = db.session.get(User, user_id)
    if user and not user.is_admin:
        user.is_active_account = not user.is_active_account
        db.session.commit()
        status = "activated" if user.is_active_account else "deactivated"
        log_action("users", f"User {status}", f"User {user.username} {status}", current_user.id)
        flash(f"User {user.username} has been {status}.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id):
    user = db.session.get(User, user_id)
    if user and not user.is_admin:
        username = user.username
        db.session.delete(user)
        db.session.commit()
        log_action("users", "User deleted", f"Deleted user {username}", current_user.id)
        flash(f"User {username} deleted.", "success")
    return redirect(url_for("admin.users"))


# --- Categories ---
@admin_bp.route("/categories")
@admin_required
def categories():
    cats = VideoCategory.query.order_by(VideoCategory.name).all()
    return render_template("admin/categories.html", categories=cats)


@admin_bp.route("/categories/add", methods=["GET", "POST"])
@admin_required
def add_category():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        desc = request.form.get("description", "")
        if not name:
            flash("Category name is required.", "danger")
        elif VideoCategory.query.filter_by(name=name).first():
            flash("Category already exists.", "danger")
        else:
            cat = VideoCategory(name=name, description=desc)
            db.session.add(cat)
            db.session.commit()
            log_action("categories", "Category added", name, current_user.id)
            flash("Category added.", "success")
            return redirect(url_for("admin.categories"))
    return render_template("admin/category_form.html", category=None)


@admin_bp.route("/categories/<int:cat_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_category(cat_id):
    cat = db.session.get(VideoCategory, cat_id)
    if not cat:
        flash("Category not found.", "danger")
        return redirect(url_for("admin.categories"))
    if request.method == "POST":
        cat.name = request.form.get("name", "").strip()
        cat.description = request.form.get("description", "")
        db.session.commit()
        flash("Category updated.", "success")
        return redirect(url_for("admin.categories"))
    return render_template("admin/category_form.html", category=cat)


@admin_bp.route("/categories/<int:cat_id>/delete", methods=["POST"])
@admin_required
def delete_category(cat_id):
    cat = db.session.get(VideoCategory, cat_id)
    if cat:
        db.session.delete(cat)
        db.session.commit()
        flash("Category deleted.", "success")
    return redirect(url_for("admin.categories"))


# --- Videos ---
@admin_bp.route("/videos")
@admin_required
def videos():
    page = request.args.get("page", 1, type=int)
    pagination = paginate_query(Video.query.order_by(Video.created_at.desc()), page)
    return render_template("admin/videos.html", pagination=pagination)


@admin_bp.route("/videos/<int:video_id>")
@admin_required
def video_detail(video_id):
    video = db.session.get(Video, video_id)
    if not video:
        flash("Video not found.", "danger")
        return redirect(url_for("admin.videos"))
    return render_template("admin/video_detail.html", video=video)


@admin_bp.route("/videos/<int:video_id>/delete", methods=["POST"])
@admin_required
def delete_video(video_id):
    video = db.session.get(Video, video_id)
    if video:
        path = os.path.join(current_app.config["UPLOAD_FOLDER"], "videos", video.filename)
        if os.path.exists(path):
            os.remove(path)
        db.session.delete(video)
        db.session.commit()
        log_action("videos", "Video deleted", video.title, current_user.id)
        flash("Video deleted.", "success")
    return redirect(url_for("admin.videos"))


# --- Detection Requests ---
@admin_bp.route("/detections")
@admin_required
def detections():
    status = request.args.get("status", "all")
    page = request.args.get("page", 1, type=int)
    query = DetectionRequest.query
    if status != "all":
        query = query.filter_by(status=status)
    pagination = paginate_query(query.order_by(DetectionRequest.created_at.desc()), page)
    return render_template("admin/detections.html", pagination=pagination, status=status)


@admin_bp.route("/detections/<int:det_id>")
@admin_required
def detection_detail(det_id):
    det = db.session.get(DetectionRequest, det_id)
    if not det:
        flash("Detection not found.", "danger")
        return redirect(url_for("admin.detections"))
    frame_data = json.loads(det.frame_analysis) if det.frame_analysis else []
    freq_data = json.loads(det.frequency_analysis) if det.frequency_analysis else {}
    return render_template("admin/detection_detail.html", detection=det, frame_data=frame_data, freq_data=freq_data)


@admin_bp.route("/detections/results")
@admin_required
def detection_results():
    label = request.args.get("label", "all")
    query = DetectionRequest.query.filter_by(status="completed")
    if label in ("real", "fake"):
        query = query.filter_by(result_label=label)
    results = query.order_by(DetectionRequest.completed_at.desc()).all()
    return render_template("admin/detection_results.html", results=results, label=label)


@admin_bp.route("/detections/<int:det_id>/report")
@admin_required
def download_report(det_id):
    det = db.session.get(DetectionRequest, det_id)
    if det and det.report_path:
        path = os.path.join(current_app.config["REPORT_FOLDER"], det.report_path)
        if os.path.exists(path):
            return send_file(path, as_attachment=True)
    flash("Report not available.", "warning")
    return redirect(url_for("admin.detection_detail", det_id=det_id))


# --- Dataset ---
@admin_bp.route("/dataset")
@admin_required
def dataset():
    label = request.args.get("label", "all")
    query = DatasetRecord.query
    if label in ("real", "fake"):
        query = query.filter_by(label=label)
    records = query.order_by(DatasetRecord.created_at.desc()).all()
    return render_template("admin/dataset.html", records=records, label=label)


@admin_bp.route("/dataset/upload", methods=["GET", "POST"])
@admin_required
def upload_dataset():
    if request.method == "POST":
        label = request.form.get("label", "real")
        files = request.files.getlist("files")
        count = 0
        for f in files:
            if f and f.filename and allowed_file(f.filename, "video"):
                ext = f.filename.rsplit(".", 1)[1].lower()
                filename = f"{label}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{count}.{ext}"
                folder = os.path.join(current_app.config["DATASET_FOLDER"], label)
                os.makedirs(folder, exist_ok=True)
                path = os.path.join(folder, filename)
                f.save(path)
                record = DatasetRecord(
                    label=label,
                    filename=filename,
                    original_filename=secure_filename(f.filename),
                    file_size=os.path.getsize(path),
                    uploaded_by=current_user.id,
                )
                db.session.add(record)
                count += 1
        db.session.commit()
        flash(f"{count} dataset sample(s) uploaded.", "success")
        return redirect(url_for("admin.dataset"))
    return render_template("admin/dataset_upload.html")


@admin_bp.route("/dataset/<int:record_id>/delete", methods=["POST"])
@admin_required
def delete_dataset(record_id):
    record = db.session.get(DatasetRecord, record_id)
    if record:
        path = os.path.join(current_app.config["DATASET_FOLDER"], record.label, record.filename)
        if os.path.exists(path):
            os.remove(path)
        db.session.delete(record)
        db.session.commit()
        flash("Dataset record deleted.", "success")
    return redirect(url_for("admin.dataset"))


# --- Settings ---
@admin_bp.route("/settings/frames", methods=["GET", "POST"])
@admin_required
def settings_frames():
    if request.method == "POST":
        settings = {
            "frame_count": int(request.form.get("frame_count", 16)),
            "frame_size": int(request.form.get("frame_size", 224)),
            "face_detection": request.form.get("face_detection") == "on",
        }
        set_setting("frame_extraction", settings, "frame")
        flash("Frame extraction settings updated.", "success")
        return redirect(url_for("admin.settings_frames"))
    settings = get_setting("frame_extraction", {})
    return render_template("admin/settings_frames.html", settings=settings)


@admin_bp.route("/settings/frequency", methods=["GET", "POST"])
@admin_required
def settings_frequency():
    if request.method == "POST":
        settings = {
            "fft_bands": int(request.form.get("fft_bands", 8)),
            "noise_threshold": float(request.form.get("noise_threshold", 0.35)),
            "texture_sensitivity": float(request.form.get("texture_sensitivity", 0.5)),
        }
        set_setting("frequency_processing", settings, "frequency")
        flash("Frequency processing settings updated.", "success")
        return redirect(url_for("admin.settings_frequency"))
    settings = get_setting("frequency_processing", {})
    return render_template("admin/settings_frequency.html", settings=settings)


@admin_bp.route("/settings/transformer", methods=["GET", "POST"])
@admin_required
def settings_transformer():
    if request.method == "POST":
        settings = {
            "layers": int(request.form.get("layers", 4)),
            "heads": int(request.form.get("heads", 4)),
            "embed_dim": int(request.form.get("embed_dim", 128)),
            "dropout": float(request.form.get("dropout", 0.1)),
        }
        set_setting("transformer_model", settings, "transformer")
        flash("Transformer model settings updated.", "success")
        return redirect(url_for("admin.settings_transformer"))
    settings = get_setting("transformer_model", {})
    return render_template("admin/settings_transformer.html", settings=settings)


# --- Model Training ---
@admin_bp.route("/model")
@admin_required
def model_status():
    training = ModelTraining.query.order_by(ModelTraining.id.desc()).first()
    accuracy_chart = []
    if training and training.accuracy_history:
        try:
            accuracy_chart = json.loads(training.accuracy_history)
        except (json.JSONDecodeError, TypeError):
            pass
    return render_template("admin/model_status.html", training=training, accuracy_chart=accuracy_chart)


@admin_bp.route("/model/train", methods=["POST"])
@admin_required
def train_model():
    records = DatasetRecord.query.all()
    if len(records) < 4:
        flash("Need at least 4 dataset samples to train.", "warning")
        return redirect(url_for("admin.model_status"))

    training = ModelTraining(
        status="training",
        epochs=int(request.form.get("epochs", 10)),
        started_at=datetime.utcnow(),
    )
    db.session.add(training)
    db.session.commit()

    def run_training(app, training_id):
        with app.app_context():
            t = db.session.get(ModelTraining, training_id)
            records = DatasetRecord.query.all()

            class DSRecord:
                def __init__(self, r):
                    self.label = r.label
                    self.file_path = os.path.join(
                        app.config["DATASET_FOLDER"], r.label, r.filename
                    )

            try:
                detector = TransformerDetector(app.config["MODEL_FOLDER"])

                def callback(epoch, loss, acc):
                    t.current_epoch = epoch
                    t.loss = round(loss, 4)
                    t.accuracy = round(acc, 2)
                    db.session.commit()

                result = detector.train_model(
                    [DSRecord(r) for r in records], epochs=t.epochs, callback=callback
                )
                t.status = "completed"
                t.loss_history = json.dumps(result["loss_history"])
                t.accuracy_history = json.dumps(result["accuracy_history"])
                t.accuracy = result["accuracy"]
                t.loss = result["loss"]
                t.model_path = result["model_path"]
                t.completed_at = datetime.utcnow()
                t.message = "Training completed successfully"
            except Exception as exc:
                t.status = "failed"
                t.message = str(exc)
                t.completed_at = datetime.utcnow()
            db.session.commit()

    thread = threading.Thread(
        target=run_training,
        args=(current_app._get_current_object(), training.id),
    )
    thread.daemon = True
    thread.start()
    flash("Model training started.", "info")
    return redirect(url_for("admin.model_status"))


@admin_bp.route("/model/update", methods=["POST"])
@admin_required
def update_model():
    try:
        detector = TransformerDetector(current_app.config["MODEL_FOLDER"])
        log_action("model", "Model updated", "Detection model reloaded from disk", current_user.id)
        flash("Detection model updated and reloaded successfully.", "success")
    except Exception as exc:
        flash(f"Model update failed: {exc}", "danger")
    return redirect(url_for("admin.model_status"))


@admin_bp.route("/model/test", methods=["POST"])
@admin_required
def test_model():
    file = request.files.get("test_file")
    if not file or not allowed_file(file.filename, "video"):
        flash("Please upload a valid video file.", "danger")
        return redirect(url_for("admin.model_status"))

    filename, path = save_upload(file, "test")
    try:
        from app.services.video_processor import VideoProcessor

        processor = VideoProcessor()
        frames = processor.extract_frames(path)
        detector = TransformerDetector(current_app.config["MODEL_FOLDER"])
        result = detector.test_sample(frames)
        flash(
            f"Test Result: {result['label'].upper()} ({result['confidence']}% confidence)",
            "success",
        )
    except Exception as exc:
        flash(f"Test failed: {exc}", "danger")
    finally:
        if os.path.exists(path):
            os.remove(path)
    return redirect(url_for("admin.model_status"))


# --- Feedback ---
@admin_bp.route("/feedback")
@admin_required
def feedback_list():
    items = Feedback.query.order_by(Feedback.created_at.desc()).all()
    return render_template("admin/feedback.html", items=items)


@admin_bp.route("/feedback/<int:item_id>/status", methods=["POST"])
@admin_required
def feedback_status(item_id):
    item = db.session.get(Feedback, item_id)
    if item:
        item.status = request.form.get("status", "reviewed")
        db.session.commit()
        flash("Feedback status updated.", "success")
    return redirect(url_for("admin.feedback_list"))


@admin_bp.route("/feedback/<int:item_id>/delete", methods=["POST"])
@admin_required
def delete_feedback(item_id):
    item = db.session.get(Feedback, item_id)
    if item:
        db.session.delete(item)
        db.session.commit()
        flash("Feedback deleted.", "success")
    return redirect(url_for("admin.feedback_list"))


# --- Contact ---
@admin_bp.route("/contacts")
@admin_required
def contacts():
    items = ContactQuery.query.order_by(ContactQuery.created_at.desc()).all()
    return render_template("admin/contacts.html", items=items)


@admin_bp.route("/contacts/<int:item_id>/reply", methods=["POST"])
@admin_required
def contact_reply(item_id):
    item = db.session.get(ContactQuery, item_id)
    if item:
        item.reply_status = request.form.get("reply_status", "replied")
        db.session.commit()
        flash("Reply status updated.", "success")
    return redirect(url_for("admin.contacts"))


@admin_bp.route("/contacts/<int:item_id>/delete", methods=["POST"])
@admin_required
def delete_contact(item_id):
    item = db.session.get(ContactQuery, item_id)
    if item:
        db.session.delete(item)
        db.session.commit()
        flash("Contact message deleted.", "success")
    return redirect(url_for("admin.contacts"))


# --- Logs & Reports ---
@admin_bp.route("/logs")
@admin_required
def logs():
    page = request.args.get("page", 1, type=int)
    pagination = paginate_query(SystemLog.query.order_by(SystemLog.created_at.desc()), page)
    return render_template("admin/logs.html", pagination=pagination)


@admin_bp.route("/login-history")
@admin_required
def login_history():
    items = LoginHistory.query.order_by(LoginHistory.created_at.desc()).limit(100).all()
    return render_template("admin/login_history.html", items=items)


@admin_bp.route("/upload-history")
@admin_required
def upload_history():
    items = UploadHistory.query.order_by(UploadHistory.created_at.desc()).limit(100).all()
    return render_template("admin/upload_history.html", items=items)


@admin_bp.route("/detection-history")
@admin_required
def detection_history():
    items = DetectionHistory.query.order_by(DetectionHistory.created_at.desc()).limit(100).all()
    return render_template("admin/detection_history.html", items=items)


@admin_bp.route("/reports/daily")
@admin_required
def daily_report():
    today = datetime.utcnow().date()
    start = datetime.combine(today, datetime.min.time())
    data = {
        "logins": LoginHistory.query.filter(LoginHistory.created_at >= start).count(),
        "uploads": UploadHistory.query.filter(UploadHistory.created_at >= start).count(),
        "detections": DetectionRequest.query.filter(DetectionRequest.created_at >= start).count(),
        "completed": DetectionRequest.query.filter(
            DetectionRequest.completed_at >= start, DetectionRequest.status == "completed"
        ).count(),
        "feedback": Feedback.query.filter(Feedback.created_at >= start).count(),
    }
    return render_template("admin/report_daily.html", data=data, date=today)


@admin_bp.route("/reports/monthly")
@admin_required
def monthly_report():
    now = datetime.utcnow()
    start = datetime(now.year, now.month, 1)
    data = {
        "logins": LoginHistory.query.filter(LoginHistory.created_at >= start).count(),
        "uploads": UploadHistory.query.filter(UploadHistory.created_at >= start).count(),
        "detections": DetectionRequest.query.filter(DetectionRequest.created_at >= start).count(),
        "real": DetectionRequest.query.filter(
            DetectionRequest.created_at >= start, DetectionRequest.result_label == "real"
        ).count(),
        "fake": DetectionRequest.query.filter(
            DetectionRequest.created_at >= start, DetectionRequest.result_label == "fake"
        ).count(),
        "users": User.query.filter(User.created_at >= start, User.role == "user").count(),
    }
    return render_template("admin/report_monthly.html", data=data, month=now.strftime("%B %Y"))
