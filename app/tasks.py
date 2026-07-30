import logging
from app.celery_app import celery_app
from app.db.database import SessionLocal
from app.services.anomaly_detection import run_anomaly_detection
from app.services.trace_events import emit_trace_events, STAGE, STATUS

logging = logging.getLogger("Tasks")

@celery_app.task(bind=True, name="run_detection", max_retries=3, default_retry_delay=5)
def run_detection(self, trace_id: str, source: str):
    '''
    '''
    db = SessionLocal()
    try:
        run_anomaly_detection(db, trace_id, source, db)
    except Exception as exception:
        logging.error(f"Detection error for {trace_id}: {exception}")
        try:
            raise self.retry(exc=exception)
        except self.MaxRetriesExceededError:
            emit_trace_events(trace_id, STAGE.DETECTION_FAILED, status=STATUS.FAILED,
                              source=source, details={"error": str(exception)})
        finally:
            db.close()