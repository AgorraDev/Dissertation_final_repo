import logging
from enum import StrEnum
from app.db.database import AuditSessionLocal
from app.db_models.sensor_models import TraceEvent

logger = logging.getLogger("TraceEvents")

class STAGE(StrEnum):
    RECEIVED = "received"
    VALIDATED = "validated"
    VALIDATION_FAILED = "validation_failed"
    PERSISTED = "persisted"
    DUPLICATE_REJECTED = "duplicate_rejected"
    DETECTION_SKIPPED = "detection_skipped"

class STATUS(StrEnum):
    OK ="ok"
    FAILED = "failed"

def emit_trace_events(trace_id, stage, status=STATUS.OK, source=None, details=None, sessionmaker_=None):
    # sessionmaker_ used for tests, AuditSessionLocal is used in production
    factory = sessionmaker_ or AuditSessionLocal

    try:
        with factory() as db:
            db.add(TraceEvent(
                trace_id=trace_id,
                stage=str(stage),
                status=str(status),
                source=source,
                details=details))
            db.commit()
    except Exception as e:
        logger.error(f"Trace emit failed - [{trace_id}/{stage}]: {e}")
        # Not raised to prevent breaking ingestion, auidt should just observe