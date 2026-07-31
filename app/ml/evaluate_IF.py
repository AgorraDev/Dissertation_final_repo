import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, precision_recall_fscore_support
from app.ml.features import features_df
from app.ml.detector import load
from app.ml.injection_IF import (load_clean_data, inject_faults,
                                 GENERATION_COL, CAPACITY_COL, PROFILE_COL)
from app.services.detection_rules import RuleContext, evaluate_all_rules

DEFAULT_CSV = "/Users/hagen/PycharmProjects/Dissertation/Data/GB_solar_timeseries_hourly_trimmed.csv"

def predict_with_rules(df):
    hours = df["timestamp"].dt.hour.to_numpy()
    months = df["timestamp"].dt.month.to_numpy()
    capacity = df[CAPACITY_COL].to_numpy()
    generation = df[GENERATION_COL].to_numpy()
    profile = df[PROFILE_COL].to_numpy()

    predictions = np.zeros(len(df), dtype=bool)
    for index in range(len(df)):
        context = RuleContext(
            hour = int(hours[index]),
            month = int(months[index]),
            capacity = float(capacity[index]),
            generation = float(generation[index]),
            solar_profile=float(profile[index]),
        )
        predictions[index] = len(evaluate_all_rules(context)) > 0
    return predictions

def predict_with_isolation_forest(df):
    artifact = load()
    model = artifact["model"]
    feature_matrix = features_df(df)
    anomaly_scores = -model.score_samples(feature_matrix)
    anomaly_flags = model.predict(feature_matrix) == -1
    return anomaly_scores, anomaly_flags

def event_recall(events, predictions, fault_type):
    matching_events = [event for event in events if event[2] == fault_type]
    if not matching_events:
        return float("nan")
    detected = sum(1 for (start, end, fault_type) in matching_events if predictions[start:end + 1].any())
    return detected / len(matching_events)

def precision_recall_f1(true_labels, predictions):
    precision, recall, f1, support = precision_recall_fscore_support(
        true_labels, predictions, average="binary", zero_division=0)
    return precision, recall, f1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default=DEFAULT_CSV)
    parser.add_argument("--start", default="2018-01-01")
    parser.add_argument("--end", default="2019-12-30")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    test_start = pd.Timestamp(args.start, tz="UTC")
    test_end = pd.Timestamp(args.end, tz="UTC") + pd.Timedelta(hours=23)
    clean_data = load_clean_data(args.data, test_start, test_end)

    injected_data, true_labels, events = inject_faults(clean_data, seed=args.seed)
    print(f"Test rows: {len(injected_data)} "
          f"injected points: {true_labels.sum()}  events: {len(events)}")

    rules_predictions = predict_with_rules(injected_data)
    isolation_forest_scores, isolation_forest_predictions = predict_with_isolation_forest(injected_data)

    rules_metrics = precision_recall_f1(true_labels, rules_predictions)
    isolation_forest_metrics = precision_recall_f1(true_labels, isolation_forest_predictions)
    isolation_forest_pr_auc = average_precision_score(true_labels, isolation_forest_scores)

    print("=====================================================")
    print("Point-Wise")
    print(f"{'detector':18}{'precision':>10}{'recall':>10}{'f1':>10}")
    print(f"{'basic-rules':18}{rules_metrics[0]:10.3f}{rules_metrics[1]:10.3f}{rules_metrics[2]:10.3f}")
    print(f"{'isolation-forest':18}{isolation_forest_metrics[0]:10.3f}"
          f"{isolation_forest_metrics[1]:10.3f}{isolation_forest_metrics[2]:10.3f}")
    print(f"Isolation Forest PR AUC: {isolation_forest_pr_auc:.3f}")
    print("\n===================================================")
    print("Event recall by fault type")
    print(f"{'fault_type':16}{'rules':>8}{'IF':>8}")
    event_recall_results = {}
    for fault_type in ["midday_dropout", "generation_spike", "nighttime_generation", "stuck_at_value", "generation_drift"]:
        rules_recall = event_recall(events, rules_predictions, fault_type)
        isolation_forest_recall = event_recall(events, isolation_forest_predictions, fault_type)
        event_recall_results[fault_type] = {"rules": rules_recall, "isolation_forest": isolation_forest_recall}
        print(f"{fault_type:16}{rules_recall:8.2f}{isolation_forest_recall:8.2f}")

    results_path = Path(__file__).resolve().parent / "evaluation_results.json"
    results_path.write_text(json.dumps({
        "test_rows": int(len(injected_data)),
        "n_anomalies": int(true_labels.sum()),
        "n_events": len(events),
        "point_wise": {
            "rules": dict(zip(["precision", "recall", "f1"], rules_metrics)),
            "isolation_forest": dict(zip(["precision", "recall", "f1"], isolation_forest_metrics)),
        },
        "iforest_pr_auc": isolation_forest_pr_auc,
        "event_recall": event_recall_results,
    }, indent=2,default=float))
    print(f"\nSaved {results_path}")

if __name__ == "__main__":
    main()

