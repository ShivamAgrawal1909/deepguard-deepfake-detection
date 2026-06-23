import json

import cv2
import numpy as np
from scipy.fftpack import dct

from app.utils.helpers import get_setting


class FrequencyAnalyzer:
    def __init__(self):
        settings = get_setting("frequency_processing", {})
        self.fft_bands = int(settings.get("fft_bands", 8))
        self.noise_threshold = float(settings.get("noise_threshold", 0.35))
        self.texture_sensitivity = float(settings.get("texture_sensitivity", 0.5))

    def analyze_frames(self, frames):
        frame_features = []
        band_energies = []
        noise_scores = []
        texture_scores = []

        for i, frame in enumerate(frames):
            gray_u8 = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = gray_u8.astype(np.float32)
            fft_mag = self._fft_magnitude(gray)
            bands = self._band_energy(fft_mag)
            noise = self._noise_pattern(gray_u8)
            texture = self._texture_irregularity(gray_u8)

            band_energies.append(bands)
            noise_scores.append(noise)
            texture_scores.append(texture)
            frame_features.append(
                {
                    "frame_index": i,
                    "noise_score": round(float(noise), 4),
                    "texture_score": round(float(texture), 4),
                    "band_energy": [round(float(b), 4) for b in bands],
                    "anomaly_flag": bool(
                        noise > self.noise_threshold or texture > self.texture_sensitivity
                    ),
                }
            )

        avg_bands = np.mean(band_energies, axis=0).tolist()
        avg_noise = float(np.mean(noise_scores))
        avg_texture = float(np.mean(texture_scores))
        anomaly_ratio = sum(1 for f in frame_features if f["anomaly_flag"]) / max(
            len(frame_features), 1
        )

        summary = {
            "average_noise": round(avg_noise, 4),
            "average_texture": round(avg_texture, 4),
            "anomaly_ratio": round(anomaly_ratio, 4),
            "dominant_bands": [round(float(b), 4) for b in avg_bands[: self.fft_bands]],
            "frequency_pattern": self._classify_pattern(avg_bands, avg_noise, avg_texture),
        }

        return {
            "frame_analysis": frame_features,
            "frequency_summary": summary,
            "feature_vector": self._build_feature_vector(avg_bands, avg_noise, avg_texture),
        }

    def _fft_magnitude(self, gray):
        f = np.fft.fft2(gray)
        fshift = np.fft.fftshift(f)
        return np.abs(fshift)

    def _band_energy(self, fft_mag):
        h, w = fft_mag.shape
        cy, cx = h // 2, w // 2
        bands = []
        max_r = min(cy, cx)
        step = max(max_r // self.fft_bands, 1)
        y, x = np.ogrid[:h, :w]
        dist_sq = (x - cx) ** 2 + (y - cy) ** 2
        for i in range(self.fft_bands):
            r_inner = i * step
            r_outer = (i + 1) * step
            r_inner_sq = r_inner ** 2
            r_outer_sq = r_outer ** 2
            mask = (dist_sq >= r_inner_sq) & (dist_sq < r_outer_sq)
            count = np.sum(mask)
            if count == 0:
                bands.append(0.0)
                continue
            energy = float(np.sum(fft_mag[mask]) / count)
            bands.append(energy)
        return np.array(bands, dtype=np.float32)

    def _noise_pattern(self, gray_u8):
        gray = gray_u8.astype(np.float32)
        laplacian = cv2.Laplacian(gray_u8, cv2.CV_64F)
        high_freq = np.std(laplacian)
        dct_coeff = dct(dct(gray, axis=0, norm="ortho"), axis=1, norm="ortho")
        hf_energy = np.mean(np.abs(dct_coeff[-16:, -16:]))
        return min(1.0, (high_freq / 50.0 + hf_energy / 30.0) / 2)

    def _texture_irregularity(self, gray_u8):
        gx = cv2.Sobel(gray_u8, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray_u8, cv2.CV_64F, 0, 1, ksize=3)
        magnitude = np.sqrt(gx**2 + gy**2)
        local_std = float(np.std(magnitude))
        return min(1.0, local_std / 80.0)

    def _classify_pattern(self, bands, noise, texture):
        high_band = float(np.mean(bands[-2:])) if len(bands) >= 2 else 0
        low_band = float(np.mean(bands[:2])) if len(bands) >= 2 else 0
        ratio = high_band / (low_band + 1e-8)
        if noise > 0.5 and texture > 0.5:
            return "High-frequency artifact pattern detected"
        if ratio > 1.8:
            return "Elevated high-frequency energy — possible manipulation"
        if noise < 0.25 and texture < 0.3:
            return "Natural frequency distribution"
        return "Mixed frequency characteristics"

    def _build_feature_vector(self, bands, noise, texture):
        vec = list(bands[: self.fft_bands])
        while len(vec) < self.fft_bands:
            vec.append(0.0)
        vec.extend([noise, texture])
        return np.array(vec, dtype=np.float32)
