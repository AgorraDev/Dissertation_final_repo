from datetime import datetime
import pandas as pd
from app.ml.features import compute_features, FEATURE_NAMES, features_df

def test_feature_vector_length():
    vector = compute_features(datetime(2016,6,21,12,0,0),
                              generation=4000.00, capacity=8000.0)

    assert len(vector) == len(FEATURE_NAMES)
    # check capacity_factor is correct - 4000 / 8000 = 0.5
    assert vector[-1] == 0.5

def test_zero_capacity_does_not_crash():
    vector = compute_features(datetime(2016,6,21,0,0,0),
                              generation=0.0, capacity=0.0)

    assert vector[-1] == 0.0

def test_online_matches_offline():
    rwo = {"utc_timestamp": "2016-06-21T12:00:00Z",
           "GB_GBN_solar_generation_actual": 4000.0, "GB_GBN_solar_capacity": 8000.0}
    offline = features_df(pd.DataFrame([rwo])).iloc[0].to_list()
    online = compute_features(datetime(2016,6,21,12,0,0),
                              generation=4000.0, capacity=8000.0)

    assert offline == online
