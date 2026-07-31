from datetime import datetime
from app.db_models.sensor_models import WeatherData, GenerationData, TraceEvent, DetectionResult
from app.services.anomaly_detection import run_anomaly_detection

def add_mock_weather_data(db, trace_id, hour=9):
    db.add(WeatherData(trace_id=trace_id, date_time=datetime(2015,6,1,hour,0,0),
                       temperature=43.15, radiation_direct_horizontal=200.00,
                       radiation_diffuse_horizontal=120.00))
    db.flush()

def add_mock_generation_data(db, trace_id):
    db.add(GenerationData(trace_id=trace_id, date_time=datetime(2016,4,17,11,0),
                          solar_capacity=7122.0, solar_generation_actual=0.0, solar_profile=0.0))
    db.flush()

def stages(db, trace_id):
    rows = db.query(TraceEvent).filter(TraceEvent.trace_id == trace_id).order_by(TraceEvent.id).all()
    return [e.stage for e in rows]

def test_scores_a_present_weather_row(db_session, audit_to_test_session):
    add_mock_weather_data(db_session, "detection-1")
    run_anomaly_detection("detection-1", "weather_data", db_session)

    assert stages(db_session, "detection-1") == ["detection_started", "scored"]
    scored = db_session.query(TraceEvent).filter(TraceEvent.trace_id == "detection-1", TraceEvent.stage == "scored").one()
    assert scored.details == {"rule_codes": [], "anomaly": False}

def test_scores_a_present_generation_row(db_session, audit_to_test_session):
    add_mock_generation_data(db_session, "detection-2")
    run_anomaly_detection("detection-2", "generation_data", db_session)

    detection_result = db_session.query(DetectionResult).filter(DetectionResult.trace_id == "detection-2").one()
    assert detection_result.anomaly == True
    assert "R1_DROPOUT_DURING_DAY_TIME" in detection_result.rule_codes

def test_skips_missing_row(db_session, audit_to_test_session):
    run_anomaly_detection("detection-3", "weather_data", db_session)

    assert stages(db_session, "detection-3") == ["detection_started", "detection_skipped"]

def test_second_run_does_not_duplicate(db_session, audit_to_test_session):
    add_mock_weather_data(db_session, "detection-4")
    run_anomaly_detection("detection-4", "weather_data", db_session)
    run_anomaly_detection("detection-4", "weather_data", db_session)

    assert stages(db_session, "detection-4") == ["detection_started", "scored"]

def test_second_run_keeps_single_detection_result(db_session, audit_to_test_session):
    add_mock_weather_data(db_session, "detection-5")
    run_anomaly_detection("detection-5", "weather_data", db_session)
    run_anomaly_detection("detection-5", "weather_data", db_session)

    assert db_session.query(DetectionResult).filter_by(trace_id="detection-5").count() == 1