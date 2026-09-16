import logging
import time
from app.core.config import settings
from app.celery_app import celery_app
from app.db.database import SessionLocal
from app.services.anomaly_detection import run_anomaly_detection
from app.services.trace_events import emit_trace_events, STAGE, STATUS

logger = logging.getLogger("Tasks")

@celery_app.task(bind=True, name="run_detection", max_retries=3, default_retry_delay=5)
def run_detection(self, trace_id: str, source: str):
    '''
    Celery task to run the anomaly detection task.
    Includes max retries for failing detection if the worker cannot process.
    '''
    db = SessionLocal()
    try:
        run_anomaly_detection(trace_id, source, db)
    except Exception as exception:
        logger.error(f"Detection error for {trace_id}: {exception}")
        if self.request.retries >= self.max_retries:
            emit_trace_events(trace_id, STAGE.DETECTION_FAILED, status=STATUS.FAILED,
                              source=source, details={"error": str(exception)})
            return
        raise self.retry(exc=exception)
    finally:
        db.close()