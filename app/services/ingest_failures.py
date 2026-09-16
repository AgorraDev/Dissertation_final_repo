import uuid
import logging
from typing import Any
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.write_record import write_new_record
from app.db_models.sensor_models import AnomalyLog, GenerationData, WeatherData
from app.services.trace_events import emit_trace_events, STATUS, STAGE

logger = logging.getLogger("IngestFailures")

'''
Called from validation_exception_handler() in main.py. 
Handles logging and writing to database of any bad data incoming into the system. 
'''


def check_float(value: Any) -> float | None:
    '''
    Check if a value is or can be floated, if not return NoneType
    Protects against bad type incoming data (nulls etc.)
    '''
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def ingest_failures(invalid_body: Any, errors: list, source: str, db: Session) -> str:
    '''
    Intercept bad data before endpoint. Parse and log bad data.
    '''
    trace_id = str(uuid.uuid4())
    body = invalid_body if isinstance(invalid_body, dict) else {}
    date_time = body.get("utc_timestamp")

    logger.error(f"Validation failure [{trace_id}] - [{source}] - reason={errors}")

    # Write to Anomaly table for error logging
    anomaly_record = AnomalyLog(
        trace_id=trace_id,
        date_time=date_time,
        source=source,
        error_details=errors,
        error_payload=body,
    )
    write_new_record(anomaly_record, trace_id, db)

    # Write to intended table to keep continuous data
    # Check source to direct write
    if source == "generation_data":
        sensor_record = GenerationData(
            trace_id=trace_id,
            date_time=date_time,
            load_actual_entsoe_transparency=check_float(body.get("GB_GBN_load_actual_entsoe_transparency")),
            load_forecast_entsoe_transparency=check_float(body.get("GB_GBN_load_forecast_entsoe_transparency")),
            price_day_ahead=check_float(body.get("GB_GBN_price_day_ahead")),
            solar_capacity=check_float(body.get("GB_GBN_solar_capacity")),
            solar_generation_actual=check_float(body.get("GB_GBN_solar_generation_actual")),
            solar_profile=check_float(body.get("GB_GBN_solar_profile")),
        )
    else:
        sensor_record = WeatherData(
            trace_id=trace_id,
            date_time=date_time,
            temperature=check_float(body.get("GB_temperature")),
            radiation_direct_horizontal=check_float(body.get("GB_radiation_direct_horizontal")),
            radiation_diffuse_horizontal=check_float(body.get("GB_radiation_diffuse_horizontal")),
        )

    write_new_record(sensor_record, trace_id, db)

    # Writes into trace_events
    emit_trace_events(
        trace_id,
        STAGE.VALIDATION_FAILED,
        status=STATUS.FAILED,
        source=source,
        details={"errors": errors},
    )
    return trace_id