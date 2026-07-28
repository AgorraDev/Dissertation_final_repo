from datetime import datetime
from email.base64mime import body_decode

from app.db_models.sensor_models import TraceEvent

TRACE_URL = "/api/v1/react/trace/{}"

def test_trace_detail_returns_ordered_chain(client, db_session):
    trace_id = "trace-detail-1"
    db_session.add_all([
        TraceEvent(trace_id=trace_id, stage="received", status="ok", source="weather_data",
                   created_at=datetime(2015,1,1,9,0,0)),
        TraceEvent(trace_id=trace_id, stage="validated", status="ok", source="weather_data",
                   created_at=datetime(2015, 1, 1, 9, 0, 1)),
        TraceEvent(trace_id=trace_id, stage="persisted", status="ok", source="weather_data",
                   created_at=datetime(2015, 1, 1, 9, 0, 2)),
        TraceEvent(trace_id="trace-detail-2", stage="received", status="ok", source="weather_data",
                   created_at=datetime(2015, 1, 1, 9, 0, 0)),
    ])
    db_session.flush()

    body = client.get(TRACE_URL.format(trace_id)).json()

    assert [e["stage"] for e in body] == ["received", "validated", "persisted"]
    assert all(e["source"] == "weather_data" for e in body)
    assert "trace_id" not in body[0]

def test_trace_detail_excludes_other_traces(client, db_session):
    db_session.add_all([
        TraceEvent(trace_id="trace-1", stage="received", status="ok", source="weather_data",
                   created_at=datetime(2015, 1, 1, 9, 0, 0)),
        TraceEvent(trace_id="trace-2", stage="received", status="ok", source="weather_data",
                   created_at=datetime(2015, 1, 1, 9, 0, 0)),
    ])
    db_session.flush()

    body = client.get(TRACE_URL.format("trace-1")).json()

    assert len(body) == 1

def test_unknown_trace_detail_returns_404(client, db_session):
    assert client.get(TRACE_URL.format("unknown-trace")).status_code == 404

def test_end_to_end_restructure_of_full_chain(client, db_session):
    '''
    Check whether we can get details of a trace id through full system lifetime.
    '''
    response = client.post("/api/v1/sensors/ingest/weather", json={
        "utc_timestamp": "2015-01-01T01:00:00Z",
        "GB_temperature": 33.0,
        "GB_radiation_direct_horizontal": 200.0,
        "GB_radiation_diffuse_horizontal": 100.0
    })
    trace_id = response.json()["trace_id"]
    body = client.get(TRACE_URL.format(trace_id)).json()
    stages = [e["stage"] for e in body]

    assert stages == ["received", "validated", "persisted"]