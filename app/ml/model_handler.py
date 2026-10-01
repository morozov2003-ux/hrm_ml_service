import os
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from app.ml.data_processor import HRMProcessor

MODEL_PATH = "/tmp/hrm_random_forest.joblib"


class HRMModelHandler:
    def __init__(self):
        self.processor = HRMProcessor()
        self.model = None

    def generate_synthetic_data(self, n_samples=300):
        """
        Генерация реалистичных кривых плавления ДНК.
        """
        X, y = [], []
        t_grid = self.processor.target_temp_grid

        for _ in range(n_samples):
            genotype = np.random.choice([0, 1, 2])
            noise = np.random.normal(0, 0.005, len(t_grid))
            background = -0.005 * t_grid + 1.4 + np.random.normal(0, 0.02)

            if genotype == 0:  # WT
                tm = 80.0 + np.random.normal(0, 0.15)
                w = 0.5 + np.random.normal(0, 0.03)
                f = 1.0 / (1.0 + np.exp((t_grid - tm) / w)) + background + noise
            elif genotype == 2:  # Mutant
                tm = 78.2 + np.random.normal(0, 0.15)
                w = 0.5 + np.random.normal(0, 0.03)
                f = 1.0 / (1.0 + np.exp((t_grid - tm) / w)) + background + noise
            else:  # Heterozygote
                tm1 = 78.2 + np.random.normal(0, 0.15)
                tm2 = 80.0 + np.random.normal(0, 0.15)
                w1 = 0.4 + np.random.normal(0, 0.03)
                w2 = 0.4 + np.random.normal(0, 0.03)
                f = 0.5 / (1.0 + np.exp((t_grid - tm1) / w1)) + \
                    0.5 / (1.0 + np.exp((t_grid - tm2) / w2)) + background + noise

            features, _ = self.processor.extract_features(t_grid, f)
            X.append(features)
            y.append(genotype)

        return np.array(X), np.array(y)

    def train_and_save(self):
        X, y = self.generate_synthetic_data()
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.model.fit(X, y)
        joblib.dump(self.model, MODEL_PATH)
        print("Model trained and saved successfully.")

    def load_model(self):
        if not os.path.exists(MODEL_PATH):
            self.train_and_save()
        self.model = joblib.load(MODEL_PATH)

    def predict(self, temperatures, fluorescence):
        if self.model is None:
            self.load_model()

        features, info = self.processor.extract_features(temperatures, fluorescence)
        features = features.reshape(1, -1)

        class_idx = int(self.model.predict(features)[0])
        probabilities = self.model.predict_proba(features)[0].tolist()

        classes_map = {0: "Wild Type (WT)", 1: "Heterozygote (Het)", 2: "Homozygous Mutant (Mut)"}

        return {
            "genotype": classes_map[class_idx],
            "class_id": class_idx,
            "confidence": float(probabilities[class_idx]),
            "tm": info["tm_estimate"],
            "probabilities": {classes_map[i]: float(p) for i, p in enumerate(probabilities)}
        }