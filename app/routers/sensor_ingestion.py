import logging
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.schemas.sensor_schemas import (
    WeatherData,
    WeatherDataTrace,
    GenerationData,
    GenerationDataTrace,
    )
from app.db.database import get_db
from app.db.write_record import write_new_record
from app.db_models.sensor_models import (
    WeatherData as WeatherDataModel,
    GenerationData as GenerationDataModel,)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Ingestion Logger")
router = APIRouter()

@router.post("/ingest/generation")
def ingest_generation_data(plant_data: GenerationData, db: Session = Depends(get_db)):
    '''
    :param db:
    :param plant_data as BaseModel
    :return: dict
    Takes schema of plant_data for generation sensors.
    Turns incoming pydantic data rows into a dict.
    This acts as the entrypoint for our backend pipeline.
    '''

    # Generate a unique id to trace the payload throughout the system.
    trace_id = str(uuid4())
    payload = {}

    payload = {
        "trace_id": trace_id,
        "source": "Generation Data",
        "date_time": plant_data.utc_timestamp,
        "load_actual_entsoe_transparency": plant_data.GB_GBN_load_actual_entsoe_transparency,
        "load_forecast_entsoe_transparency": plant_data.GB_GBN_load_forecast_entsoe_transparency,
        "price_day_ahead": plant_data.GB_GBN_price_day_ahead,
        "solar_capacity": plant_data.GB_GBN_solar_capacity,
        "solar_generation_actual": plant_data.GB_GBN_solar_generation_actual,
        "solar_profile": plant_data.GB_GBN_solar_profile,
    }
    new_record = GenerationDataModel (
        trace_id=trace_id,
        date_time=plant_data.utc_timestamp,
        load_actual_entsoe_transparency=plant_data.GB_GBN_load_actual_entsoe_transparency,
        load_forecast_entsoe_transparency=plant_data.GB_GBN_load_forecast_entsoe_transparency,
        price_day_ahead=plant_data.GB_GBN_price_day_ahead,
        solar_capacity=plant_data.GB_GBN_solar_capacity,
        solar_generation_actual=plant_data.GB_GBN_solar_generation_actual,
        solar_profile=plant_data.GB_GBN_solar_profile,
    )

    write_new_record(new_record, trace_id, db)

    # Print payload items for verification.
    print("------------------------------------------------------------------------")
    for item in payload:
        print(f"{item}: {payload[item]} - {type(payload[item])}")
    print("------------------------------------------------------------------------")

    ## TODO: SEND 'payload' to DAILY_READINGS TABLE
    return payload

@router.post("/ingest/weather")
def ingest_weather_data(plant_data: WeatherData, db: Session = Depends(get_db)):
    trace_id = str(uuid4())
    payload = {}

    payload = {
        "trace_id": trace_id,
        "source": "Weather Sensor Data",
        "date_time": plant_data.utc_timestamp,
        "temperature": plant_data.GB_temperature,
        "radiation_direct_horizontal": plant_data.GB_radiation_direct_horizontal,
        "radiation_diffuse_horizontal": plant_data.GB_radiation_diffuse_horizontal,
    }
    new_record = WeatherDataModel (
        trace_id=trace_id,
        date_time=plant_data.utc_timestamp,
        temperature=plant_data.GB_temperature,
        radiation_direct_horizontal=plant_data.GB_radiation_direct_horizontal,
        radiation_diffuse_horizontal=plant_data.GB_radiation_diffuse_horizontal,
    )

    write_new_record(new_record, trace_id, db)

    #Print payload items for verification.
    print("------------------------------------------------------------------------")
    for item in payload:
        print(f"{item}: {payload[item]} - {type(payload[item])}")
    print("------------------------------------------------------------------------")

    ## TODO: SEND 'payload' to DAILY_READINGS TABLE
    return payload