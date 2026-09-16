from datetime import datetime

from app.db_models.sensor_models import AnomalyLog, WeatherData, GenerationData, DetectionResult
from app.schemas.sensor_schemas import DetectionResultOut

WEATHER_URL = "/api/v1/react/weather"
GENERATION_URL = "/api/v1/react/generation"
ANOMALY_URL = "/api/v1/react/anomaly_log"
DETECTIONS_URL = "/api/v1/react/detections"

def add_detection(db, trace_id, anomaly, rule_codes, hour=11):
    db.add(DetectionResult(
        trace_id=trace_id, detector="basic-rules", detector_version="v1.0",
        source="generation_data", date_time=datetime(2016,4,17,hour,0,0),
        anomaly=anomaly, score=None, rule_codes=rule_codes, details={"rule_codes": rule_codes, "anomaly": anomaly},
    ))
    db.flush()

def test_weather_endpoint_returns_seeded_row(client, db_session):
    db_session.add(WeatherData(
        trace_id="weather_trace_1",
        date_time=datetime(2015, 1, 1, 9, 0 ,0),
        temperature= -2.4,
        radiation_direct_horizontal=34.5,
        radiation_diffuse_horizontal=12.3,
    ))
    db_session.flush()

    body = client.get(WEATHER_URL).json()

    assert len(body) == 1
    row = body[0]
    assert set(row) == {
        "trace_id",
        "utc_timestamp",
        "GB_temperature",
        "GB_radiation_direct_horizontal",
        "GB_radiation_diffuse_horizontal",
    }
    assert row["trace_id"] == "weather_trace_1"
    assert row["GB_temperature"] == -2.4

def test_generation_endpoint_returns_seeded_row(client, db_session):
    db_session.add(GenerationData(
        trace_id="generation_trace_1",
        date_time=datetime(2015, 1, 1, 9, 0 ,0),
        load_actual_entsoe_transparency= 10.0,
        load_forecast_entsoe_transparency=20.0,
        price_day_ahead=2.0,
        solar_capacity=40.0,
        solar_generation_actual=30.0,
        solar_profile=50.0,
    ))
    db_session.flush()

    body = client.get(GENERATION_URL).json()
    assert len(body) == 1
    row = body[0]
    assert set(row) == {
        "trace_id",
        "utc_timestamp",
        "GB_GBN_load_actual_entsoe_transparency",
        "GB_GBN_load_forecast_entsoe_transparency",
        "GB_GBN_price_day_ahead",
        "GB_GBN_solar_capacity",
        "GB_GBN_solar_generation_actual",
        "GB_GBN_solar_profile",
    }
    assert row["trace_id"] == "generation_trace_1"
    assert row["GB_GBN_solar_generation_actual"] == 30.0

def test_anomaly_endpoint_returns_seeded_row(client, db_session):
    db_session.add(AnomalyLog(
        trace_id="anomaly_trace_1",
        date_time=datetime(2015, 1, 1, 9, 0 ,0),
        source="weather data",
        error_details=[{"loc": ["body", "GB_temperature"], "msg": "Input should be a valid number"}],
        error_payload={"utc_timestamp": "2015-01-01T09:00:00Z", "GB_temperature": None,},
    ))
    db_session.flush()

    body = client.get(ANOMALY_URL).json()
    assert len(body) == 1
    row = body[0]
    assert set(row) == {"trace_id", "date_time", "source", "error_details", "error_payload"}
    assert row["trace_id"] == "anomaly_trace_1"
    assert row["source"] == "weather data"
    assert row["error_payload"]["GB_temperature"] is None

def test_empty_tables_return_empty_list(client):
    assert client.get(WEATHER_URL).json() == []
    assert client.get(GENERATION_URL).json() == []
    assert client.get(ANOMALY_URL).json() == []

def test_detections_endpoint_returns_seeded_row(client, db_session):
    add_detection(db_session, "detection_trace_1", True, ["R1_DROPOUT_DURING_DAY_TIME"])

    body = client.get(DETECTIONS_URL).json()

    assert len(body) == 1
    row = body[0]
    assert set(row) == {
        "trace_id", "detector", "detector_version", "source", "date_time", "anomaly", "score", "rule_codes",
        "details", "created_at",
    }
    assert row["trace_id"] == "detection_trace_1"
    assert row["anomaly"] is True
    assert row["rule_codes"] == ["R1_DROPOUT_DURING_DAY_TIME"]

def test_detections_only_anomalies_filter(client, db_session):
    add_detection(db_session, "clean-detection", False, [], hour=12)
    add_detection(db_session, "anomaly-detection", True, ["R1_DROPOUT_DURING_DAY_TIME"], hour=11)

    all_rows = client.get(DETECTIONS_URL).json()
    anom_rows = client.get(DETECTIONS_URL, params={"anomalies_only": "true"}).json()

    assert len(all_rows) == 2
    assert len(anom_rows) == 1
    assert anom_rows[0]["trace_id"] == "anomaly-detection"

def test_detections_empty_table_returns_empty_list(client):
    assert client.get(DETECTIONS_URL).json() == []