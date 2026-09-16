import pytest
from datetime import datetime
from app.ml.detector import score_reading, MODEL_PATH

pytestmark = pytest.mark.skipif(not MODEL_PATH, reason="No model found. IF not trained")

def test_iforest_expected_shape_returns():
    result = score_reading(datetime(2019,6,21,12,0,0),
                           generation=6000.0, capacity=8000.0)

    assert set(result) == {"anomaly", "score", "version", "features"}
    assert isinstance(result["anomaly"], bool)

def test_iforest_ranks_dropout_above_healthy():
    healthy_result = score_reading(datetime(2019,6,21,12,0,0),
                                   generation=6000.0, capacity=8000.0)
    dropout_result = score_reading(datetime(2019,6,21,12,0,0),
                                   generation=0.0, capacity=8000.0)

    assert dropout_result["score"] > healthy_result["score"]