import numpy as np
import pandas as pd

FEATURE_NAMES = ["hour_sin", "hour_cos", "day_sin", "day_cos", "capacity_factor"]

def compute_features(timestamp, generation: float, capacity: float) -> list[float]:

    hour = timestamp.hour
    day = timestamp.timetuple().tm_yday
    capacity_factor = generation / capacity if capacity else 0
    return [
        # Calculating cyclical hour/day so model can learn normal generation for
        # time of year + day. Allows IF to read 00.00 as next to 23.00 and same for jan/dec.
        np.sin(2 * np.pi * hour / 24),
        np.cos(2 * np.pi * hour / 24),
        np.sin(2 * np.pi * day / 366),
        np.cos(2 * np.pi * day / 366),
        # Normalised again here to allow for growth of capacity over years
        capacity_factor
    ]

def features_df(df, timestamp_column="utc_timestamp",
                    generation_column="GB_GBN_solar_generation_actual",
                    capacity_column="GB_GBN_solar_capacity",):
    timestamp = pd.to_datetime(df[timestamp_column], utc=True)
    generation = df[generation_column].astype(float)
    capacity = df[capacity_column].astype(float)
    capacity_factor = (generation / capacity).where(capacity != 0, 0.0)
    output = pd.DataFrame({
        "hour_sin": np.sin(2 * np.pi * timestamp.dt.hour / 24),
        "hour_cos": np.cos(2 * np.pi * timestamp.dt.hour / 24),
        "day_sin": np.sin(2 * np.pi * timestamp.dt.dayofyear / 366),
        "day_cos": np.cos(2 * np.pi * timestamp.dt.dayofyear / 366),
        "capacity_factor": capacity_factor,
    })
    return output[FEATURE_NAMES]