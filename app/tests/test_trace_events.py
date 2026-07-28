from datetime import datetime, timedelta, timezone
from app.db_models.sensor_models import TraceEvent
from app.services.trace_events import STAGE, STATUS, emit_trace_events

def test_emits_event_with_all_fields(db_session, audit_factory):
    emit_trace_events(
        trace_id="trace-1",
        stage=STAGE.PERSISTED,
        status=STATUS.OK,
        source="weather_data",
        details={"row_id": 2},
        sessionmaker_=audit_factory,
    )

    event = db_session.query(TraceEvent).filter_by(trace_id="trace-1").one()
    assert event.stage == "persisted"
    assert event.status == "ok"
    assert event.source == "weather_data"
    assert event.details == {"row_id": 2}

def test_status_defaults_to_ok(db_session, audit_factory):
    emit_trace_events(
        trace_id="trace-2",
        stage=STAGE.RECEIVED,
        sessionmaker_=audit_factory,
    )

    event = db_session.query(TraceEvent).filter_by(trace_id="trace-2").one()
    assert event.status == "ok"
    assert event.source is None
    assert event.details is None

def test_created_at_is_evaluated_per_row(db_session, audit_factory):
    '''
    Using callable lambda function in SQLAlchemy sensor model. This test checks that
    the created_at field is getting called at each insert and not once when imported.
    '''
    before = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=5)
    emit_trace_events("trace-3", STAGE.RECEIVED, sessionmaker_=audit_factory)
    event = db_session.query(TraceEvent).filter_by(trace_id="trace-3").one()
    assert event.created_at is not None
    assert event.created_at >= before

def test_multiple_events_from_an_ordered_chain(db_session, audit_factory):
    '''
    Testing to ensure a trace_id can be assigned to multiple events so a chain
    can be formed throughout the system.
    '''
    for stage in (STAGE.RECEIVED, STAGE.VALIDATED, STAGE.PERSISTED):
        emit_trace_events("trace-4", stage, sessionmaker_=audit_factory)

    events = (db_session.query(TraceEvent).filter_by(trace_id="trace-4").order_by(TraceEvent.id).all())

    assert [e.stage for e in events] == ["received", "validated", "persisted"]
    assert [e.created_at for e in events] == sorted(e.created_at for e in events)

def test_failure_is_recorded(db_session, audit_factory):
    emit_trace_events(
        trace_id="trace-5",
        stage=STAGE.VALIDATION_FAILED, status=STATUS.FAILED,
        details={"errors": [{"loc": ["body", "GB_GBN_solar_capacity"]}]},
        source="generation_data", sessionmaker_=audit_factory)

    event = db_session.query(TraceEvent).filter_by(trace_id="trace-5").one()
    assert event.status == "failed"
    assert event.details["errors"][0]["loc"] == ["body", "GB_GBN_solar_capacity"]

def test_details_survive_as_jsonb(db_session, audit_factory):
    payload = {"score": {"iforest": -0.21, "lstm": -0.83}, "model_versions": ["if-v2", "lstm-v1"],
               "flagged": True, "note": None}

    emit_trace_events("trace-6", STAGE.PERSISTED, details=payload, sessionmaker_=audit_factory)

    event = db_session.query(TraceEvent).filter_by(trace_id="trace-6").one()
    assert event.details == payload

