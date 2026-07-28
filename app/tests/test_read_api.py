from datetime import datetime

from app.db_models.sensor_models import AnomalyLog, WeatherData, GenerationData

WEATHER_URL = "/api/v1/react/weather"
GENERATION_URL = "/api/v1/react/generation"
ANOMALY_URL = "/api/v1/react/anomaly_log"

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