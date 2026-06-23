"""Seed database with dummy data for DeepGuard application."""

import json
import os
import random
from datetime import datetime, timedelta

import cv2
import numpy as np

from app import create_app, db
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


def create_sample_video(path, label="real", frames=30):
    """Generate a synthetic test video for seeding."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    h, w = 224, 224
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(path, fourcc, 10.0, (w, h))
    for i in range(frames):
        if label == "real":
            frame = np.random.randint(80, 180, (h, w, 3), dtype=np.uint8)
            cv2.circle(frame, (w // 2, h // 2), 40, (200, 160, 140), -1)
        else:
            frame = np.random.randint(0, 255, (h, w, 3), dtype=np.uint8)
            noise = np.random.randint(0, 80, (h, w, 3), dtype=np.uint8)
            frame = cv2.addWeighted(frame, 0.7, noise, 0.3, 0)
            cv2.circle(frame, (w // 2, h // 2), 40, (180, 140, 120), -1)
        out.write(frame)
    out.release()


def create_sample_image(path, label="real"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    h, w = 224, 224
    if label == "real":
        img = np.random.randint(80, 180, (h, w, 3), dtype=np.uint8)
        cv2.circle(img, (w // 2, h // 2), 50, (200, 160, 140), -1)
    else:
        img = np.random.randint(0, 255, (h, w, 3), dtype=np.uint8)
    cv2.imwrite(path, img)


def seed_database():
    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()

        upload_dir = app.config["UPLOAD_FOLDER"]
        dataset_dir = app.config["DATASET_FOLDER"]

        # Admin
        admin = User(
            username="admin",
            email="admin@deepguard.com",
            full_name="System Administrator",
            phone="9876543210",
            role="admin",
        )
        admin.set_password("admin123")
        db.session.add(admin)

        # 8 dummy users
        users_data = [
            ("john_doe", "john@email.com", "John Doe", "9123456780"),
            ("jane_smith", "jane@email.com", "Jane Smith", "9123456781"),
            ("mike_wilson", "mike@email.com", "Mike Wilson", "9123456782"),
            ("sarah_jones", "sarah@email.com", "Sarah Jones", "9123456783"),
            ("david_brown", "david@email.com", "David Brown", "9123456784"),
            ("emily_davis", "emily@email.com", "Emily Davis", "9123456785"),
            ("chris_miller", "chris@email.com", "Chris Miller", "9123456786"),
            ("lisa_taylor", "lisa@email.com", "Lisa Taylor", "9123456787"),
        ]
        users = []
        for username, email, name, phone in users_data:
            u = User(username=username, email=email, full_name=name, phone=phone, role="user")
            u.set_password("user123")
            if username == "chris_miller":
                u.is_active_account = False
            users.append(u)
            db.session.add(u)
        db.session.flush()

        # Categories
        categories_data = [
            ("Interview", "Interview and talking-head videos"),
            ("News", "News broadcast clips"),
            ("Social Media", "Social media video content"),
            ("Entertainment", "Entertainment and celebrity videos"),
            ("Education", "Educational video content"),
            ("Surveillance", "CCTV and surveillance footage"),
            ("Personal", "Personal video recordings"),
            ("Documentary", "Documentary footage"),
        ]
        categories = []
        for name, desc in categories_data:
            cat = VideoCategory(name=name, description=desc)
            categories.append(cat)
            db.session.add(cat)
        db.session.flush()

        # Videos and detections
        os.makedirs(os.path.join(upload_dir, "videos"), exist_ok=True)
        os.makedirs(os.path.join(upload_dir, "thumbnails"), exist_ok=True)

        detection_statuses = [
            ("completed", "real", 87.5),
            ("completed", "fake", 92.3),
            ("completed", "real", 78.9),
            ("completed", "fake", 95.1),
            ("pending", None, None),
            ("failed", None, None),
            ("completed", "real", 91.2),
            ("completed", "fake", 88.7),
        ]

        for i, user in enumerate(users[:8]):
            vpath = os.path.join(upload_dir, "videos", f"seed_video_{i}.mp4")
            create_sample_video(vpath, label="real" if i % 2 == 0 else "fake")
            fsize = os.path.getsize(vpath)
            thumb = f"thumb_seed_{i}.jpg"
            cap = cv2.VideoCapture(vpath)
            ret, frame = cap.read()
            cap.release()
            if ret:
                cv2.imwrite(os.path.join(upload_dir, "thumbnails", thumb), frame)

            video = Video(
                user_id=user.id,
                category_id=categories[i % len(categories)].id,
                title=f"Sample Video {i + 1}",
                filename=f"seed_video_{i}.mp4",
                original_filename=f"sample_{i + 1}.mp4",
                file_size=fsize,
                duration=3.0,
                format="mp4",
                thumbnail=thumb,
                status="uploaded",
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
            )
            db.session.add(video)
            db.session.flush()

            status, label, conf = detection_statuses[i]
            det = DetectionRequest(
                user_id=user.id,
                video_id=video.id,
                request_type="video",
                status=status,
                result_label=label,
                confidence=conf,
                frame_analysis=json.dumps([
                    {"frame_index": j, "noise_score": round(random.uniform(0.1, 0.6), 4),
                     "texture_score": round(random.uniform(0.1, 0.5), 4),
                     "band_energy": [round(random.uniform(0.1, 1.0), 4) for _ in range(8)],
                     "anomaly_flag": random.random() > 0.6}
                    for j in range(8)
                ]) if status == "completed" else None,
                frequency_analysis=json.dumps({
                    "average_noise": round(random.uniform(0.2, 0.5), 4),
                    "average_texture": round(random.uniform(0.15, 0.45), 4),
                    "anomaly_ratio": round(random.uniform(0.1, 0.4), 4),
                    "dominant_bands": [round(random.uniform(0.1, 1.0), 4) for _ in range(8)],
                    "frequency_pattern": "Natural frequency distribution" if label == "real" else "High-frequency artifact pattern detected",
                }) if status == "completed" else None,
                summary=f"Detection Result: {label.upper()} ({conf}% confidence)." if label else None,
                error_message="Frame extraction failed" if status == "failed" else None,
                created_at=video.created_at + timedelta(minutes=5),
                completed_at=video.created_at + timedelta(minutes=10) if status != "pending" else None,
            )
            db.session.add(det)

        # Dataset records (8 samples)
        for i in range(8):
            label = "real" if i % 2 == 0 else "fake"
            fname = f"dataset_{label}_{i}.mp4"
            fpath = os.path.join(dataset_dir, label, fname)
            create_sample_video(fpath, label=label)
            record = DatasetRecord(
                label=label,
                filename=fname,
                original_filename=f"training_{label}_{i}.mp4",
                file_size=os.path.getsize(fpath),
                uploaded_by=admin.id,
            )
            db.session.add(record)

        # Feedback (8 items)
        feedback_subjects = [
            "Great detection accuracy",
            "Slow processing time",
            "UI improvement suggestion",
            "False positive report",
            "Feature request: batch upload",
            "Excellent frame analysis",
            "Mobile support needed",
            "Report download issue",
        ]
        for i, user in enumerate(users):
            fb = Feedback(
                user_id=user.id,
                subject=feedback_subjects[i],
                message=f"This is sample feedback message #{i + 1} from {user.username}.",
                status=["pending", "reviewed", "resolved"][i % 3],
                created_at=datetime.utcnow() - timedelta(days=i),
            )
            db.session.add(fb)

        # Contact queries (8 items)
        contact_data = [
            ("Alice Cooper", "alice@mail.com", "Partnership Inquiry", "Interested in enterprise licensing."),
            ("Bob Martin", "bob@mail.com", "Technical Support", "Need help with video upload."),
            ("Carol White", "carol@mail.com", "Demo Request", "Would like a product demo."),
            ("Dan Green", "dan@mail.com", "Pricing Question", "What are the pricing plans?"),
            ("Eva Black", "eva@mail.com", "API Integration", "Do you offer API access?"),
            ("Frank Blue", "frank@mail.com", "Bug Report", "Detection page loading slowly."),
            ("Grace Red", "grace@mail.com", "Training Data", "Can we contribute training data?"),
            ("Henry Gold", "henry@mail.com", "General Inquiry", "Tell me more about the technology."),
        ]
        for i, (name, email, subject, msg) in enumerate(contact_data):
            cq = ContactQuery(
                name=name, email=email, subject=subject, message=msg,
                reply_status="replied" if i % 2 == 0 else "pending",
                created_at=datetime.utcnow() - timedelta(days=i * 2),
            )
            db.session.add(cq)

        # Model training record
        training = ModelTraining(
            status="completed",
            epochs=10,
            current_epoch=10,
            accuracy=94.5,
            loss=0.0823,
            loss_history=json.dumps([0.65, 0.45, 0.32, 0.21, 0.15, 0.12, 0.10, 0.09, 0.085, 0.0823]),
            accuracy_history=json.dumps([55.0, 68.0, 75.0, 82.0, 86.0, 89.0, 91.0, 92.5, 93.8, 94.5]),
            message="Initial training completed with seed dataset",
            started_at=datetime.utcnow() - timedelta(days=5),
            completed_at=datetime.utcnow() - timedelta(days=5, hours=-1),
        )
        db.session.add(training)

        # System logs
        log_entries = [
            ("auth", "Admin login", "System initialized"),
            ("users", "User registered", "john_doe registered"),
            ("upload", "Video uploaded", "Sample Video 1 uploaded"),
            ("detection", "Detection completed", "Result: REAL 87.5%"),
            ("detection", "Detection completed", "Result: FAKE 92.3%"),
            ("model", "Training completed", "Accuracy: 94.5%"),
            ("settings", "Settings updated", "Frame extraction settings changed"),
            ("security", "Password changed", "Admin changed password"),
        ]
        for log_type, action, details in log_entries:
            db.session.add(SystemLog(log_type=log_type, action=action, details=details, user_id=admin.id))

        # Login history
        for user in [admin] + users[:5]:
            db.session.add(LoginHistory(
                user_id=user.id, username=user.username, role=user.role,
                ip_address="127.0.0.1", status="success",
                created_at=datetime.utcnow() - timedelta(hours=random.randint(1, 48)),
            ))

        # Upload & detection history
        for i in range(8):
            db.session.add(UploadHistory(
                user_id=users[i % len(users)].id,
                filename=f"seed_video_{i}.mp4",
                file_type="video",
                file_size=random.randint(100000, 5000000),
                status="success",
            ))

        db.session.commit()
        print("=" * 50)
        print("Database seeded successfully!")
        print("=" * 50)
        print("Admin Login: admin / admin123")
        print("User Login:  john_doe / user123 (and 7 more users)")
        print("=" * 50)


if __name__ == "__main__":
    seed_database()
