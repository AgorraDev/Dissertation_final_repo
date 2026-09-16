import logging
from app.core.config import settings
from enum import StrEnum
from app.db.database import AuditSessionLocal
from app.db_models.sensor_models import TraceEvent

logger = logging.getLogger("TraceEvents")

# set Stage enum as strings
class STAGE(StrEnum):
    RECEIVED = "received"
    VALIDATED = "validated"
    VALIDATION_FAILED = "validation_failed"
    PERSISTED = "persisted"
    DUPLICATE_REJECTED = "duplicate_rejected"
    ENQUEUED = "enqueued"
    DETECTION_STARTED = "detection_started"
    SCORED = "scored"
    DETECTION_SKIPPED = "detection_skipped"
    DETECTION_FAILED = "detection_failed"

class STATUS(StrEnum):
    OK ="ok"
    FAILED = "failed"

# trace levels are assigned int values for easy comparison with >=
LEVEL_RANK = {"off": 0, "minimal": 1, "full": 2}

# set stages to fire based on config level.
# this controls what is recorded at each trace level
STAGE_MINIMAL_LEVEL = {
    STAGE.SCORED: "minimal",
    STAGE.VALIDATION_FAILED: "minimal",
    STAGE.DUPLICATE_REJECTED: "minimal",
    STAGE.DETECTION_SKIPPED: "minimal",
    STAGE.DETECTION_FAILED: "minimal",
    STAGE.RECEIVED: "full",
    STAGE.VALIDATED: "full",
    STAGE.PERSISTED: "full",
    STAGE.ENQUEUED: "full",
    STAGE.DETECTION_STARTED: "full",
}

# Check the configured trace level and handles emission based on the above minimal levels.
# If the configured level is lower than the required, it will not emit.
def emit_enabled(stage) -> bool:
    configured = LEVEL_RANK[settings.TRACE_LEVEL]
    required = LEVEL_RANK[STAGE_MINIMAL_LEVEL.get(stage, "full")]
    return configured >= required

def emit_trace_events(trace_id, stage, status=STATUS.OK, source=None, details=None, sessionmaker_=None):
    # Don't emit if the below the configured level
    # full by default to emit all, minimal and off used for comparative analysis
    if not emit_enabled(stage):
        return
    # sessionmaker_ used for tests, AuditSessionLocal for live
    factory = sessionmaker_ or AuditSessionLocal

    try:
        with factory() as db:
            # write trace to database (emit trace)
            db.add(TraceEvent(
                trace_id=trace_id,
                stage=str(stage),
                status=str(status),
                source=source,
                details=details)
            )
            db.commit()
    except Exception as e:
        logger.error(f"Trace emit failed - [{trace_id}/{stage}]: {e}")
        # Not raised to prevent breaking ingestion, audit should just observe