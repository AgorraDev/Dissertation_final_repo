import joblib
import argparse
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import sklearn
from sklearn.ensemble import IsolationForest
from app.ml.features import features_df, FEATURE_NAMES

DATA_CSV = "/Users/hagen/PycharmProjects/Dissertation/Data/GB_solar_timeseries_hourly_trimmed.csv"
MODEL_DIR = Path(__file__).resolve().parent / "models"
MODEL_VERSION = "v1.0"
RANDOM_SEED = 42
CONTAMINATION = 0.01
N_ESTIMATORS = 100

VALIDATION_COLS = [
    "GB_GBN_load_actual_entsoe_transparency",
    "GB_GBN_load_forecast_entsoe_transparency",
    "GB_GBN_price_day_ahead",
    "GB_GBN_solar_capacity",
    "GB_GBN_solar_generation_actual",
    "GB_GBN_solar_profile",
]

def load_valid(csv_path, start, end):
    df = pd.read_csv(csv_path)
    timestamp = pd.to_datetime(df["utc_timestamp"], utc=True)
    df = df[(timestamp >= start) & (timestamp <= end)].copy()

    return df.dropna(subset=VALIDATION_COLS)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default=DATA_CSV)
    # Default start/end allows for 2 years of training
    parser.add_argument("--train-start", default="2015-01-01")
    parser.add_argument("--train-end", default="2017-12-31")
    args = parser.parse_args()

    start = pd.Timestamp(args.train_start, tz=timezone.utc)
    end = pd.Timestamp(args.train_end, tz=timezone.utc) + pd.Timedelta(hours=23)
    df = load_valid(args.data, start, end)
    X = features_df(df)

    model = IsolationForest(
        n_estimators=N_ESTIMATORS,
        contamination=CONTAMINATION,
        random_state=RANDOM_SEED
    ).fit(X)

    MODEL_DIR.mkdir(exist_ok=True)
    artifact = {
        "model": model,
        "feature_names": FEATURE_NAMES,
        "metadata": {
            "version": MODEL_VERSION,
            "trained_on": f"{args.train_start}-{args.train_end}",
            "train_rows": int(len(X)),
            "contamination": CONTAMINATION,
            "n_estimators": N_ESTIMATORS,
            "random_state": RANDOM_SEED,
            "sklearn_version": sklearn.__version__,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    }
    output = MODEL_DIR / f"isolation_forest_{MODEL_VERSION}.joblib"
    joblib.dump(artifact, output)
    print(f"Trained Isolation Forest on {len(X)} samples: {output}")
    print(artifact["metadata"])

if __name__ == "__main__":
    main()