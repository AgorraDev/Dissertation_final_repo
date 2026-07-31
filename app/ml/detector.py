import joblib
import logging
from pathlib import Path
from app.ml.features import compute_features

logger = logging.getLogger("IForestDetector")

DETECTOR_NAME = "isolation-forest"
MODEL_PATH = Path(__file__).resolve().parent / "models" / "isolation_forest_v1.0.joblib"

artifact = None

def load():
    # global ensures celery loads the model once and not on each row read.
    global artifact
    if artifact is None:
        if not MODEL_PATH.exists():
            logger.warning(f"IForest model not found at {MODEL_PATH}: Skipping IForest detection")
            return None

        artifact = joblib.load(MODEL_PATH)
    return artifact

def score_reading(timestamp, generation: float, capacity: float) -> dict | None:
    art = load()
    if art is None:
        return None
    features = [compute_features(timestamp, generation, capacity)]
    prediction = art["model"].predict(features)[0]
    raw = art["model"].score_samples(features)[0]
    return {
            "anomaly": bool(prediction == -1),
            "score": float(raw),
            "version": art["metadata"]["version"],}
