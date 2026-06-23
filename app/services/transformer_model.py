import json
import math
import os

import numpy as np
import torch
import torch.nn as nn

from app.utils.helpers import get_setting


class PositionalEncoding(nn.Module):
    def __init__(self, d_model, max_len=64):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(
            torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model)
        )
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer("pe", pe.unsqueeze(0))

    def forward(self, x):
        return x + self.pe[:, : x.size(1)]


class DeepfakeTransformer(nn.Module):
    def __init__(self, input_dim, embed_dim, num_layers, num_heads, dropout=0.1):
        super().__init__()
        self.input_proj = nn.Linear(input_dim, embed_dim)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=embed_dim,
            nhead=num_heads,
            dim_feedforward=embed_dim * 4,
            dropout=dropout,
            batch_first=True,
        )
        self.pos_encoder = PositionalEncoding(embed_dim)
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.classifier = nn.Sequential(
            nn.LayerNorm(embed_dim),
            nn.Linear(embed_dim, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, 2),
        )

    def forward(self, x):
        x = self.input_proj(x)
        x = self.pos_encoder(x)
        x = self.transformer(x)
        x = x.mean(dim=1)
        return self.classifier(x)


class TransformerDetector:
    def __init__(self, model_dir):
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)
        settings = get_setting("transformer_model", {})
        self.layers = int(settings.get("layers", 4))
        self.heads = int(settings.get("heads", 4))
        self.embed_dim = int(settings.get("embed_dim", 128))
        self.dropout = float(settings.get("dropout", 0.1))
        self.input_dim = 10
        self.model = DeepfakeTransformer(
            self.input_dim, self.embed_dim, self.layers, self.heads, self.dropout
        )
        self.model_path = os.path.join(model_dir, "detector.pt")
        self._load_if_exists()

    def _load_if_exists(self):
        if os.path.exists(self.model_path):
            self.model.load_state_dict(torch.load(self.model_path, map_location="cpu"))
        self.model.eval()

    def predict(self, frame_features_list, frequency_vector):
        seq = []
        for feat in frame_features_list:
            bands = feat.get("band_energy", [0] * 8)[:8]
            while len(bands) < 8:
                bands.append(0.0)
            seq.append(bands + [feat.get("noise_score", 0), feat.get("texture_score", 0)])

        if len(seq) < 1:
            seq = [frequency_vector.tolist()]

        x = torch.tensor([seq], dtype=torch.float32)
        with torch.no_grad():
            logits = self.model(x)
            probs = torch.softmax(logits, dim=1)[0]
            fake_prob = float(probs[1].item())
            real_prob = float(probs[0].item())

        label = "fake" if fake_prob >= real_prob else "real"
        confidence = max(fake_prob, real_prob) * 100

        freq_boost = self._frequency_heuristic(frequency_vector)
        if freq_boost > 0.55 and label == "real":
            label = "fake"
            confidence = max(confidence, freq_boost * 100)
        elif freq_boost < 0.35 and label == "fake" and confidence < 70:
            label = "real"
            confidence = max(confidence, (1 - freq_boost) * 100)

        return {
            "label": label,
            "confidence": round(confidence, 2),
            "real_probability": round(real_prob * 100, 2),
            "fake_probability": round(fake_prob * 100, 2),
        }

    def _frequency_heuristic(self, freq_vector):
        if len(freq_vector) < 2:
            return 0.5
        noise = float(freq_vector[-2]) if len(freq_vector) >= 2 else 0.5
        texture = float(freq_vector[-1]) if len(freq_vector) >= 1 else 0.5
        return min(1.0, (noise + texture) / 2)

    def train_model(self, dataset_records, epochs=10, callback=None):
        if len(dataset_records) < 4:
            raise ValueError("Need at least 4 dataset samples to train")

        from app.services.frequency_analysis import FrequencyAnalyzer
        from app.services.video_processor import VideoProcessor

        analyzer = FrequencyAnalyzer()
        processor = VideoProcessor()
        X_list, y_list = [], []

        for record in dataset_records:
            path = record.file_path
            try:
                if path.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".webp")):
                    frames = processor.extract_from_image(path)
                else:
                    frames = processor.extract_frames(path)
                result = analyzer.analyze_frames(frames)
                seq = []
                for feat in result["frame_analysis"]:
                    bands = feat["band_energy"][:8]
                    while len(bands) < 8:
                        bands.append(0.0)
                    seq.append(bands + [feat["noise_score"], feat["texture_score"]])
                X_list.append(seq)
                y_list.append(1 if record.label == "fake" else 0)
            except Exception:
                continue

        if len(X_list) < 4:
            raise ValueError("Insufficient valid samples after processing")

        max_len = max(len(s) for s in X_list)
        padded = []
        for seq in X_list:
            while len(seq) < max_len:
                seq.append([0.0] * 10)
            padded.append(seq)

        X = torch.tensor(padded, dtype=torch.float32)
        y = torch.tensor(y_list, dtype=torch.long)

        optimizer = torch.optim.Adam(self.model.parameters(), lr=0.001)
        criterion = nn.CrossEntropyLoss()
        self.model.train()

        loss_history = []
        acc_history = []

        for epoch in range(epochs):
            optimizer.zero_grad()
            logits = self.model(X)
            loss = criterion(logits, y)
            loss.backward()
            optimizer.step()

            with torch.no_grad():
                preds = logits.argmax(dim=1)
                acc = (preds == y).float().mean().item()

            loss_history.append(round(float(loss.item()), 4))
            acc_history.append(round(acc * 100, 2))
            if callback:
                callback(epoch + 1, loss.item(), acc * 100)

        self.model.eval()
        torch.save(self.model.state_dict(), self.model_path)
        return {
            "accuracy": acc_history[-1] if acc_history else 0,
            "loss": loss_history[-1] if loss_history else 0,
            "loss_history": loss_history,
            "accuracy_history": acc_history,
            "model_path": self.model_path,
        }

    def test_sample(self, frames):
        from app.services.frequency_analysis import FrequencyAnalyzer

        analyzer = FrequencyAnalyzer()
        result = analyzer.analyze_frames(frames)
        return self.predict(result["frame_analysis"], result["feature_vector"])
