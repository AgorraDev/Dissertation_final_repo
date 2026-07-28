import logging
from sqlalchemy.orm import Session
from app.db.write_record import write_new_record
from app.db_models.sensor_models import GenerationData, WeatherData
from app.services.trace_events import emit_trace_events, STAGE, STATUS

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

    # True unless duplicate insert is rejected
    is_written = write_new_record(record, trace_id, db)

    emit_trace_events(
        trace_id,
        STAGE.PERSISTED if is_written else STAGE.DUPLICATE_REJECTED,
        status=STATUS.OK,
        source=source,
        details={"date_time": plant_data.utc_timestamp.isoformat()},
    )
    return is_written