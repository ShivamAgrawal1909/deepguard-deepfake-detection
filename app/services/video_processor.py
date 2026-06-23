import json
import math
import os

import cv2
import numpy as np
from PIL import Image

from app.utils.helpers import get_setting


class VideoProcessor:
    def __init__(self):
        settings = get_setting("frame_extraction", {})
        self.frame_count = int(settings.get("frame_count", 16))
        self.frame_size = int(settings.get("frame_size", 224))
        self.face_detection = bool(settings.get("face_detection", True))
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

    def validate_video(self, path):
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            return False, "Unable to open video file"
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 25
        duration = frame_count / fps if fps else 0
        cap.release()
        if frame_count < 1:
            return False, "Video contains no readable frames"
        max_size = 100 * 1024 * 1024
        if os.path.getsize(path) > max_size:
            return False, "Video exceeds maximum size of 100MB"
        return True, {"frame_count": frame_count, "fps": fps, "duration": duration}

    def extract_frames(self, path):
        cap = cv2.VideoCapture(path)
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        indices = np.linspace(0, max(total - 1, 0), self.frame_count, dtype=int)
        frames = []
        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
            ret, frame = cap.read()
            if not ret:
                continue
            if self.face_detection:
                frame = self._crop_face(frame)
            frame = cv2.resize(frame, (self.frame_size, self.frame_size))
            frames.append(frame)
        cap.release()
        if not frames:
            raise ValueError("No frames could be extracted from video")
        return frames

    def extract_from_image(self, path):
        img = cv2.imread(path)
        if img is None:
            raise ValueError("Unable to read image file")
        if self.face_detection:
            img = self._crop_face(img)
        img = cv2.resize(img, (self.frame_size, self.frame_size))
        return [img]

    def save_thumbnail(self, path, output_path):
        cap = cv2.VideoCapture(path)
        ret, frame = cap.read()
        cap.release()
        if ret:
            cv2.imwrite(output_path, frame)
            return True
        return False

    def _crop_face(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
        if len(faces) == 0:
            return frame
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
        pad = int(0.1 * max(w, h))
        x1 = max(0, x - pad)
        y1 = max(0, y - pad)
        x2 = min(frame.shape[1], x + w + pad)
        y2 = min(frame.shape[0], y + h + pad)
        return frame[y1:y2, x1:x2]
