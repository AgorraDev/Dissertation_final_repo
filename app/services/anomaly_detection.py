import logging
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.db_models.sensor_models import WeatherData, GenerationData, TraceEvent, DetectionResult
from app.services.trace_events import emit_trace_events, STATUS, STAGE
from app.services.detection_rules import create_context, evaluate_all_rules, DETECTOR_NAME, DETECTOR_VERSION

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

def record_detection(db, trace_id: str, source: str, date_time, rule_codes: list[str]) -> bool:

    record = pg_insert(DetectionResult).values(
        trace_id=trace_id,
        detector=DETECTOR_NAME,
        detector_version=DETECTOR_VERSION,
        source=source,
        date_time=date_time,
        anomaly=bool(rule_codes),
        score=None,
        rule_codes=rule_codes,
        details={"rule_codes": rule_codes, "anomaly": bool(rule_codes)},
    ).on_conflict_do_nothing(
        index_elements=["trace_id", "detector", "detector_version"],
    )

    result = db.execute(record)
    db.commit()
    return result.rowcount == 1

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

    if source == "generation_data":
        rule_codes = evaluate_all_rules(create_context(row))
    else:
        rule_codes = []

    inserted = record_detection(db, trace_id, source, row.date_time, rule_codes)
    if inserted:
        emit_trace_events(trace_id, STAGE.SCORED, source=source, details={"rule_codes": rule_codes,
                                                                          "anomaly": bool(rule_codes)})
