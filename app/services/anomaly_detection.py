import logging
from app.db_models.sensor_models import WeatherData, GenerationData, TraceEvent
from app.services.trace_events import emit_trace_events, STATUS, STAGE

logger = logging.getLogger("AnomalyDetection")

LEAF_STAGES = [
    str(STAGE.SCORED),
    str(STAGE.DETECTION_FAILED),
    str(STAGE.DETECTION_SKIPPED)
]

def already_processed(db, trace_id: str) -> bool:
    '''
    Query the database to see if a trace has been assigned a leaf stage.
    If True we end the worker early.
    '''
    return db.query(TraceEvent).filter(
        TraceEvent.trace_id==trace_id, TraceEvent.stage.in_(LEAF_STAGES),
    ).first() is not None

def run_stub_detector(row) -> dict:
    return {"detector": "stub", "anomaly": False}

def run_anomaly_detection(trace_id: str, source: str, db) -> None:
    if already_processed(db, trace_id):
        logger.info(f"Skipping anomaly detection for {trace_id}")
        return

    emit_trace_events(trace_id, STAGE.DETECTION_STARTED, source=source)

    data_model = GenerationData if source == "generation_data" else WeatherData
    row = db.query(data_model).filter(data_model.trace_id==trace_id).first()

    if row is None:
        emit_trace_events(trace_id, STAGE.DETECTION_SKIPPED, source=source,
                          details={"reason": "Row not found"})
        return

    result = run_stub_detector(row)
    emit_trace_events(trace_id, STAGE.SCORED, source=source, details=result)



