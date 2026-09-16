import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

logger = logging.getLogger("WriteRecord")

def write_new_record(record_data, trace_id: str, db: Session) -> bool:
    '''Attempt to write a new record to the database.
    Return True if the record was successfully written, False and rollback otherwise. Raise on SQL Error
    '''
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