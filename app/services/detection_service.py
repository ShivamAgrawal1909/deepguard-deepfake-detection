import json
import os
from datetime import datetime

from flask import current_app

from app import db
from app.models import DetectionRequest
from app.services.frequency_analysis import FrequencyAnalyzer
from app.services.transformer_model import TransformerDetector
from app.services.video_processor import VideoProcessor
from app.utils.helpers import log_detection_history


class DetectionService:
    def __init__(self):
        self.processor = VideoProcessor()
        self.analyzer = FrequencyAnalyzer()
        self.detector = TransformerDetector(current_app.config["MODEL_FOLDER"])

    def process_detection(self, detection_id):
        detection = db.session.get(DetectionRequest, detection_id)
        if not detection:
            return False, "Detection request not found"

        try:
            if detection.request_type == "video":
                video = detection.video
                path = os.path.join(
                    current_app.config["UPLOAD_FOLDER"], "videos", video.filename
                )
                valid, info = self.processor.validate_video(path)
                if not valid:
                    raise ValueError(info)
                frames = self.processor.extract_frames(path)
            else:
                path = os.path.join(
                    current_app.config["UPLOAD_FOLDER"], "images", detection.image_filename
                )
                frames = self.processor.extract_from_image(path)

            freq_result = self.analyzer.analyze_frames(frames)
            prediction = self.detector.predict(
                freq_result["frame_analysis"], freq_result["feature_vector"]
            )

            detection.status = "completed"
            detection.result_label = prediction["label"]
            detection.confidence = prediction["confidence"]
            detection.frame_analysis = json.dumps(freq_result["frame_analysis"])
            detection.frequency_analysis = json.dumps(freq_result["frequency_summary"])
            detection.summary = self._build_summary(prediction, freq_result)
            detection.completed_at = datetime.utcnow()
            detection.report_path = self._generate_report(detection, prediction, freq_result)

            db.session.commit()
            log_detection_history(detection)
            return True, detection

        except Exception as exc:
            detection.status = "failed"
            detection.error_message = str(exc)
            detection.completed_at = datetime.utcnow()
            db.session.commit()
            log_detection_history(detection)
            return False, str(exc)

    def _build_summary(self, prediction, freq_result):
        fs = freq_result["frequency_summary"]
        return (
            f"Detection Result: {prediction['label'].upper()} "
            f"({prediction['confidence']}% confidence). "
            f"Frequency pattern: {fs['frequency_pattern']}. "
            f"Anomaly ratio across frames: {fs['anomaly_ratio']:.2%}."
        )

    def _generate_report(self, detection, prediction, freq_result):
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        report_name = f"report_{detection.id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
        report_path = os.path.join(current_app.config["REPORT_FOLDER"], report_name)
        os.makedirs(current_app.config["REPORT_FOLDER"], exist_ok=True)

        doc = SimpleDocTemplate(report_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph("Deepfake Detection Report", styles["Title"]))
        story.append(Spacer(1, 12))
        story.append(Paragraph(f"Request ID: {detection.id}", styles["Normal"]))
        story.append(Paragraph(f"Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", styles["Normal"]))
        story.append(Spacer(1, 12))
        story.append(Paragraph(f"<b>Result:</b> {prediction['label'].upper()}", styles["Heading2"]))
        story.append(Paragraph(f"<b>Confidence:</b> {prediction['confidence']}%", styles["Normal"]))
        story.append(Spacer(1, 12))
        story.append(Paragraph("<b>Frequency Analysis Summary</b>", styles["Heading3"]))
        fs = freq_result["frequency_summary"]
        freq_data = [
            ["Metric", "Value"],
            ["Average Noise", str(fs["average_noise"])],
            ["Average Texture", str(fs["average_texture"])],
            ["Anomaly Ratio", str(fs["anomaly_ratio"])],
            ["Pattern", fs["frequency_pattern"]],
        ]
        table = Table(freq_data, colWidths=[200, 300])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4f8")]),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 12))
        story.append(Paragraph(f"<b>Summary:</b> {detection.summary}", styles["Normal"]))
        doc.build(story)
        return report_name
