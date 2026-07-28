from app.db_models.sensor_models import AnomalyLog, WeatherData, GenerationData, TraceEvent
from app.tests.conftest import db_session
from datetime import datetime

''' WEATHER SENSOR TESTS'''

WEATHER_URL = "/api/v1/sensors/ingest/weather"

VALID_WEATHER = {
    "utc_timestamp": "2015-01-01T09:00:00Z",
    "GB_temperature": 4.1,
    "GB_radiation_direct_horizontal": 55.00,
    "GB_radiation_diffuse_horizontal": 21.0,
}

def test_valid_weather_returns_trace_id_and_persists(client, db_session):
    response = client.post(WEATHER_URL, json=VALID_WEATHER)

    assert response.status_code == 200
    trace_id = response.json()["trace_id"]
    row = db_session.query(WeatherData).filter_by(trace_id=trace_id).one()
    assert row.temperature == 4.1

def test_null_temperature_returns_422_and_logs_anomaly(client, db_session):
    payload = dict(VALID_WEATHER, utc_timestamp="2015-01-01T10:00:00Z", GB_temperature=None)

    response = client.post(WEATHER_URL, json=payload)

    assert response.status_code == 422

    trace_id = response.json()["trace_id"]
    assert db_session.query(AnomalyLog).filter_by(trace_id=trace_id).count() == 1

def test_negative_radiation_returns_422_and_logs_anomaly(client, db_session):
    payload = dict(VALID_WEATHER, GB_radiation_direct_horizontal= -1.0)
    response = client.post(WEATHER_URL, json=payload)

    assert response.status_code == 422

    trace_id = response.json()["trace_id"]
    assert db_session.query(AnomalyLog).filter_by(trace_id=trace_id).count() == 1

def test_missing_timestamp_does_not_crash_handler(client, db_session):
    response = client.post(WEATHER_URL, json={"GB_temperature": 1.0})
    assert response.status_code == 422

def test_weather_duplicate_timestamp_does_not_duplicate_db_record(client, db_session):
    response = client.post(WEATHER_URL, json=VALID_WEATHER)
    assert response.status_code == 200
    client.post(WEATHER_URL, json=VALID_WEATHER)
    assert db_session.query(WeatherData).filter_by(
        date_time=datetime(2015, 1, 1, 9, 0, 0)).count() == 1

def test_validation_failure_emits_failed_attempt(client, db_session):
    response = client.post(WEATHER_URL, json={
                "utc_timestamp": "2015-01-01T09:00:00Z",
                 "GB_temperature": None,
                 "GB_radiation_direct_horizontal": 0.0,
                 "GB_radiation_diffuse_horizontal": 0.0,
                })
    trace_id = response.json()["trace_id"]

    events = db_session.query(TraceEvent).filter_by(
        trace_id=trace_id, stage="validation_failed").all()
    assert len(events) == 1
    assert events[0].status == "failed"
    assert events[0].details["errors"]

'''GENERATION TESTS'''

GENERATION_URL = "/api/v1/sensors/ingest/generation"

VALID_GENERATION = {
    "utc_timestamp": "2015-01-01T09:00:00Z",
    "GB_GBN_load_actual_entsoe_transparency": 100.00,
    "GB_GBN_load_forecast_entsoe_transparency": 200.00,
    "GB_GBN_price_day_ahead": 150.00,
    "GB_GBN_solar_capacity": 1000.00,
    "GB_GBN_solar_generation_actual": 500.00,
    "GB_GBN_solar_profile": 0.30,
}

def test_valid_generation_returns_trace_id_and_persists(client, db_session):
    response = client.post(GENERATION_URL, json=VALID_GENERATION)

    assert response.status_code == 200
    trace_id = response.json()["trace_id"]
    assert db_session.query(GenerationData).filter_by(trace_id=trace_id).count() == 1

def test_negative_solar_capacity_returns_422_and_logs_anomaly(client, db_session):
    payload = dict(VALID_GENERATION, GB_GBN_solar_capacity=-1.0)

    response = client.post(GENERATION_URL, json=payload)
    assert response.status_code == 422
    trace_id = response.json()["trace_id"]
    assert db_session.query(AnomalyLog).filter_by(trace_id=trace_id).count() == 1

def test_bad_data_type_returns_422_and_logs_anomaly(client, db_session):
    payload = dict(VALID_GENERATION, GB_GBN_solar_generation_actual= "abc")

    response = client.post(GENERATION_URL, json=payload)
    assert response.status_code == 422

    trace_id = response.json()["trace_id"]
    assert db_session.query(AnomalyLog).filter_by(trace_id=trace_id).count() == 1

def test_generation_duplicate_timestamp_does_not_duplicate_db_record(client, db_session):
    response = client.post(GENERATION_URL, json=VALID_GENERATION)
    assert response.status_code == 200
    client.post(GENERATION_URL, json=VALID_GENERATION)
    assert db_session.query(GenerationData).filter_by(
        date_time=datetime(2015, 1, 1, 9, 0, 0)).count() == 1

def test_duplicate_persists_are_rejected_though_data_rolls_back(client, db_session):
    client.post(GENERATION_URL, json=VALID_GENERATION)
    client.post(GENERATION_URL, json=VALID_GENERATION)

    # assert one row survived duplicate insert on unique constraint (timestamp)
    assert db_session.query(GenerationData).filter_by(
        date_time=datetime(2015, 1, 1, 9, 0, 0)).count() == 1

    # assert rejection is still recorded
    stages = [e.stage for e in db_session.query(TraceEvent).order_by(TraceEvent.id). all()]
    assert "persisted" in stages
    assert "duplicate_rejected" in stages


