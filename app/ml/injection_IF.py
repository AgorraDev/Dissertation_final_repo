import numpy as np
import pandas as pd

GENERATION_COL = "GB_GBN_solar_generation_actual"
CAPACITY_COL = "GB_GBN_solar_capacity"
PROFILE_COL = "GB_GBN_solar_profile"

VALIDATION_COLS = [
    "GB_GBN_load_actual_entsoe_transparency",
    "GB_GBN_load_forecast_entsoe_transparency",
    "GB_GBN_price_day_ahead",
    "GB_GBN_solar_capacity",
    "GB_GBN_solar_generation_actual",
    "GB_GBN_solar_profile",
]

def load_clean_data(csv_path, start, end):
    df = pd.read_csv(csv_path)
    timestamps = pd.to_datetime(df["utc_timestamp"], utc=True)
    in_range = (timestamps >= start) & (timestamps <= end)
    df = df[in_range].dropna(subset=VALIDATION_COLS).reset_index(drop=True)
    df["timestamp"] = pd.to_datetime(df["utc_timestamp"], utc=True)
    return df

def overwrite_generation(df, positions, new_generation_values):
    positions = list(positions)
    df.loc[positions, GENERATION_COL] = new_generation_values

    capacity = df.loc[positions, CAPACITY_COL].to_numpy()
    safe_capacity = np.where(capacity > 0, capacity, 1.0)
    df.loc[positions, PROFILE_COL] = np.where(capacity > 0, np.asarray(new_generation_values) / safe_capacity, 0.0)

def inject_faults(df, seed=42, faults_per_type=20, window_size=5):
    random_generator = np.random.default_rng(seed)
    df = df.copy()
    rows = len(df)
    labels = np.zeros(rows, dtype=bool)
    events = []
    hour_of_day = df["timestamp"].dt.hour.to_numpy()

    def pick_start_positions(hour, how_many, needed_width):
        candidates = np.where(hour)[0]
        candidates = candidates[candidates + needed_width < rows]
        how_many_available = min(how_many, len(candidates))
        return random_generator.choice(candidates,size=how_many_available, replace=False)

    # Injects generation falling to 0 for several hours during middle of the day
    for start in pick_start_positions((hour_of_day >= 9) & (hour_of_day <=11), faults_per_type, window_size):
        end = start + window_size - 1
        overwrite_generation(df, range(start, end + 1), np.zeros(window_size))
        labels[start:end + 1] = True
        events.append((start, end, "midday_dropout"))

    # Injects generation exceeding capacity
    for start in pick_start_positions((hour_of_day >= 8) & (hour_of_day <= 16), faults_per_type, 0):
        generation_spike_value = df[CAPACITY_COL].iloc[start] * 1.3
        overwrite_generation(df, [start], [generation_spike_value])
        labels[start] = True
        events.append((start, start, "generation_spike"))

    # Injects nighttime generation
    for start in pick_start_positions((hour_of_day <= 1) | (hour_of_day >= 23), faults_per_type, 0):
        nighttime_value = df[CAPACITY_COL].iloc[start] * 0.05
        overwrite_generation(df, [start], [nighttime_value])
        labels[start] = True
        events.append((start, start, "nighttime_generation"))

    # Injects repeated values over several hours
    for start in pick_start_positions((hour_of_day >= 8) & (hour_of_day <= 15), faults_per_type, window_size):
        end = start + window_size - 1
        stuck_value = df[GENERATION_COL].iloc[start]
        overwrite_generation(df, range(start, end + 1), np.full(window_size, stuck_value))
        labels[start:end + 1] = True
        events.append((start, end, "stuck_at_value"))

    # Injects gradual drift (generation decaying over a long window)
    for start in pick_start_positions((hour_of_day >= 8) & (hour_of_day <= 15), faults_per_type, window_size*2):
        drift_width = window_size * 2
        end = start + drift_width - 1
        original_values = df[GENERATION_COL].iloc[start:end + 1].to_numpy()
        decay = np.linspace(1.0,0.3, drift_width)
        overwrite_generation(df, range(start, end + 1), original_values * decay)
        labels[start:end + 1] = True
        events.append((start, end, "generation_drift"))

    return df, labels, events
