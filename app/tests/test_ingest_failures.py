from app.db_models.sensor_models import AnomalyLog, GenerationData, WeatherData
from app.services.ingest_failures import ingest_failures


def test_null_temperature_persists_anomaly_and_padded_row(db_session):
    body = {
        "utc_timestamp": "2015-01-01T05:00:00Z",
        "GB_temperature": None,
        "GB_radiation_direct_horizontal": 12.5,
        "GB_radiation_diffuse_horizontal": 3.2,
    }
    errors = [{"loc": ["body", "GB_temperature"], "msg": "Input should be a valid number"}]

    trace_id = ingest_failures(body, errors, "weather_data", db_session)

    anomaly = db_session.query(AnomalyLog).filter_by(trace_id=trace_id).one()
    padded = db_session.query(WeatherData).filter_by(trace_id=trace_id).one()
    assert anomaly.source == "weather_data"
    assert padded.temperature is None
    assert padded.radiation_direct_horizontal == 12.5   # fails while the key-name bug lives


def test_generation_failure_writes_generation_table(db_session):
    body = {
        "utc_timestamp": "2015-01-02T11:00:00Z",
        "GB_GBN_load_actual_entsoe_transparency": 30123.0,
        "GB_GBN_load_forecast_entsoe_transparency": 29800.0,
        "GB_GBN_price_day_ahead": 41.2,
        "GB_GBN_solar_capacity": None,
        "GB_GBN_solar_generation_actual": 512.0,
        "GB_GBN_solar_profile": 0.06,
    }
    trace_id = ingest_failures(body, [{"msg": "..."}], "generation_data", db_session)

    padded = db_session.query(GenerationData).filter_by(trace_id=trace_id).one()
    assert padded.solar_capacity is None
    assert padded.price_day_ahead == 41.2


def test_garbage_body_still_returns_trace_id(db_session):
    trace_id = ingest_failures("not even a dict", [], "weather_data", db_session)
    assert db_session.query(AnomalyLog).filter_by(trace_id=trace_id).count() == 1