import logging
from sqlalchemy.orm import Session
from app.db.write_record import write_new_record
from app.db_models.sensor_models import GenerationData, WeatherData
from app.services.trace_events import emit_trace_events, STAGE, STATUS
from app.tasks import run_detection

logger = logging.getLogger("IngestSuccess")

def ingest_success(plant_data, source: str, trace_id: str, db: Session) -> bool:

    if source == "generation_data":
        record = GenerationData(
            trace_id=trace_id,
            date_time=plant_data.utc_timestamp,
            load_actual_entsoe_transparency=plant_data.GB_GBN_load_actual_entsoe_transparency,
            load_forecast_entsoe_transparency=plant_data.GB_GBN_load_forecast_entsoe_transparency,
            price_day_ahead=plant_data.GB_GBN_price_day_ahead,
            solar_capacity=plant_data.GB_GBN_solar_capacity,
            solar_generation_actual=plant_data.GB_GBN_solar_generation_actual,
            solar_profile=plant_data.GB_GBN_solar_profile,
        )
    else:
        record = WeatherData(
            trace_id=trace_id,
            date_time=plant_data.utc_timestamp,
            temperature=plant_data.GB_temperature,
            radiation_direct_horizontal=plant_data.GB_radiation_direct_horizontal,
            radiation_diffuse_horizontal=plant_data.GB_radiation_diffuse_horizontal,
    )

    # Write record to db
    is_written = write_new_record(record, trace_id, db)

    #if not written then failed as duplicate
    emit_trace_events(
        trace_id,
        STAGE.PERSISTED if is_written else STAGE.DUPLICATE_REJECTED,
        status=STATUS.OK,
        source=source,
        details={"date_time": plant_data.utc_timestamp.isoformat()},
    )
    # if written emit as enqueued and attempt to add to worker queue
    if is_written:
        emit_trace_events(trace_id, STAGE.ENQUEUED, source=source)
        try:
            # Enqueue to celery worker
            # Using delay runs detection task inline meaning it retains the logical chain order 'persisted -> enqueued'
            run_detection.delay(trace_id, source)
        except Exception as exception:
            # On exception, detection is skipped and status set to failed. Written to db
            emit_trace_events(trace_id, STAGE.DETECTION_SKIPPED, status=STATUS.FAILED,
                              source=source, details={"reason": f"enqueue failed: {exception}"})

    return is_written