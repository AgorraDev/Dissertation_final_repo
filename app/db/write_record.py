import logging
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger("WriteRecord")

def write_new_record(record_data, trace_id: str, db: Session):
    try:
        db.add(record_data)
        db.commit()
        logger.info(f"Record collected for trace: {trace_id}")
        db.refresh(record_data)
    except IntegrityError as e:
        db.rollback()
        logger.error(f"IntegrityError - Rolling back database")
