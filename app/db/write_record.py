import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

logger = logging.getLogger("WriteRecord")

def write_new_record(record_data, trace_id: str, db: Session) -> bool:
    try:
        db.add(record_data)
        db.commit()
        logger.info(f"Record written for trace: {trace_id}")
        return True
    except IntegrityError as e:
        db.rollback()
        logger.warning(f"IntegrityError on trace: {trace_id} - Rolling back database")
        return False
    except SQLAlchemyError as e:
        logger.error(f"Write failed for trace: {trace_id} - {e}")
        db.rollback()
        raise