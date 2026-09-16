import logging
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.db_models.sensor_models import WeatherData, GenerationData, TraceEvent, DetectionResult
from app.services.trace_events import emit_trace_events, STATUS, STAGE
from app.services.detection_rules import (create_context, evaluate_all_rules,
                                          DETECTOR_NAME as RULES_DETECTOR, DETECTOR_VERSION as RULES_VERSION)
from app.ml.detector import score_reading, DETECTOR_NAME as IF_DETECTOR

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

def record_detection(db, trace_id, source, date_time, detector, version,
                     anomaly, rule_codes, score=None, details=None) -> bool:

    record = pg_insert(DetectionResult).values(
        trace_id=trace_id,
        detector=detector,
        detector_version=version,
        source=source,
        date_time=date_time,
        anomaly=bool(anomaly),
        score=score,
        rule_codes=rule_codes,
        details=details or {},
    ).on_conflict_do_nothing(
        index_elements=["trace_id", "detector", "detector_version"],
    )
    # Returns True if db count is 1 (a record already exists)
    return db.execute(record).rowcount == 1

def run_anomaly_detection(trace_id: str, source: str, db) -> None:
    '''
    Defines anomaly detection logic that is run by the Celery worker.
    Write a record to the trace_events table based on outcome of detection.
    '''

    if already_processed(db, trace_id):
        logger.info(f"Skipping anomaly detection for {trace_id}")
        return

    # Emit event as detection started.
    emit_trace_events(trace_id, STAGE.DETECTION_STARTED, source=source)

    # Set data model type based on source of the data
    data_model = GenerationData if source == "generation_data" else WeatherData

    # Query the db based on the trace id.
    # If not found emit as detection failed.
    row = db.query(data_model).filter(data_model.trace_id==trace_id).first()
    if row is None:
        emit_trace_events(trace_id, STAGE.DETECTION_SKIPPED, status=STATUS.FAILED, source=source,
                          details={"reason": "Row not found"})
        return

    inserted = False
    flagged = {}

    # Rules detection
    rule_codes = evaluate_all_rules(create_context(row)) if source == "generation_data" else []
    if record_detection(db, trace_id, source, row.date_time, RULES_DETECTOR, RULES_VERSION,
                        anomaly=bool(rule_codes), rule_codes=rule_codes,
                        details={"rule_codes": rule_codes, "anomaly": bool(rule_codes)}):
        inserted = True
        flagged[RULES_DETECTOR] = bool(rule_codes)

    #Isolation Forest
    if source == "generation_data":
        result = score_reading(row.date_time, row.solar_generation_actual, row.solar_capacity)
        if result is not None:
            if record_detection(db, trace_id, source, row.date_time, IF_DETECTOR, result["version"],
                                anomaly=result["anomaly"], rule_codes=[],
                                score=result["score"],
                                details={"score": result["score"], "anomaly": result["anomaly"],
                                            "features": result["features"]}):
                inserted = True
                flagged[IF_DETECTOR] = result["anomaly"]
    db.commit()

    if inserted:
        emit_trace_events(trace_id, STAGE.SCORED, source=source, details={"detectors": flagged})