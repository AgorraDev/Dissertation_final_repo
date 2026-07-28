from datetime import datetime

from app.db.write_record import write_new_record
from app.db_models.sensor_models import WeatherData

def weather_row(trace_id: str, hour: int) -> WeatherData:
    return WeatherData(
        trace_id=trace_id,
        date_time=datetime(2015, 1, 1, hour, 0, 0),
        temperature=35.0,
        radiation_direct_horizontal=200.00,
        radiation_diffuse_horizontal=80.00,
    )

def test_returns_true_and_persists_on_sucess(db_session):
    result = write_new_record(weather_row("trace-good", 9), "trace-good", db_session)

    assert result is True
    assert db_session.query(WeatherData).filter_by(trace_id="trace-good").count() == 1

def test_returns_false_on_duplicate_timestamp(db_session):
    write_new_record(weather_row("first-trace", 10), "first-trace", db_session)
    result = write_new_record(weather_row("second-trace", 10), "second-trace", db_session)

    assert result is False
    assert db_session.query(WeatherData).filter_by(date_time=datetime(2015, 1, 1, 10, 0)).count() == 1
    assert db_session.query(WeatherData).filter_by(trace_id="second-trace").count() == 0

def test_session_remains_usable_after_duplicate_rollback(db_session):
    write_new_record(weather_row('first-trace', 11), "first-trace", db_session)
    write_new_record(weather_row('second-trace', 11), "second-trace", db_session)

    result = write_new_record(weather_row("third-trace", 12), "third-trace", db_session)

    assert result is True
    assert db_session.query(WeatherData).filter_by(trace_id="third-trace").count() == 1