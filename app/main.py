import logging, uuid
from contextlib import asynccontextmanager
from sqlite3 import OperationalError

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

from app.db.database import engine, SessionLocal
from app.db.write_record import write_new_record
from app.db_models import sensor_models
from app.db_models.sensor_models import (
            AnomalyLog as AnomalyLogModel,
            GenerationData as GenerationDataModel,
            WeatherData as WeatherSensorModel
            )

from app.routers import sensor_ingestion, react_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("System Log")

logger.info("Logging system information")

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting lifespan")

    print("Checking database connection...")
    try:
        with engine.connect() as conn:
            logger.info("Database connection established!")

            try:
                sensor_models.Base.metadata.create_all(bind=engine)
            except OperationalError as e:
                logger.error(F"Failed to create database tables: {e}")

    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise e

    yield

    logger.info("Shutting down. Closing database connection...")
    engine.dispose()
    logger.info("Database connection closed.")
app = FastAPI(lifespan=lifespan)

origins = [
    'http://localhost',
    'http://localhost:5173',
    'http://127.0.0.1:8000',
    'http://localhost:3000',
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(
    sensor_ingestion.router,
    prefix="/api/v1/sensors",
    tags=["sensor_ingestion"]
)
app.include_router(
    react_router.router,
    prefix="/api/v1/react",
    tags=["react"]
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    '''
    Intercept bad data before endpoint. Parse and log bad data.
    '''
    trace_id = str(uuid.uuid4())
    invalid_body = exc.body if isinstance(exc.body, dict) else {}
    invalid_payload = {
        "trace_id": trace_id,
        "event": "validation_error",
        "date_time": invalid_body["utc_timestamp"],
        "source": "weather_data" if "GB_temperature" in invalid_body else "generation_data",
        "reasons": [exc.errors()],
        "bad_data": invalid_body
    }
    logger.error(f"Validation Failure:\n{invalid_payload.get("reasons")}")

    ## TODO SEND 'invalid_payload' to database ERROR_PAYLOAD TABLE and DAILY_READINGS TABLE

    # Open session, try to write to Anomaly Log table, then close session
    # Cannot use Depends as it is reserved for router endpoints
    db = SessionLocal()
    try:
        # Write to anomaly table
        anomaly_record = AnomalyLogModel(
            trace_id=trace_id,
            date_time=invalid_payload.get("date_time"),
            source=invalid_payload.get("source"),
            error_details=invalid_payload.get("reasons")[0][0],
            error_payload=invalid_payload.get("bad_data"),
        )
        write_new_record(anomaly_record, trace_id, db)

        # and to generation/weather tables so we have continuous data
        if "SOLAR_CAPACITY" in invalid_payload.get("bad_data"):
            new_generation_record = GenerationDataModel(
                trace_id=trace_id,
                date_time=invalid_body["utc_timestamp"],
                load_actual_entsoe_transparency=invalid_body["GB_GBN_load_actual_entsoe_transparency"],
                load_forecast_entsoe_transparency=invalid_body["GB_GBN_load_forecast_entsoe_transparency"],
                price_day_ahead=invalid_body["GB_GBN_price_day_ahead"],
                solar_capacity=invalid_body["GB_GBN_solar_capacity"],
                solar_generation_actual=invalid_body["GB_GBN_solar_generation_actual"],
                solar_profile=invalid_body["GB_GBN_solar_profile"],
            )
            write_new_record(new_generation_record, trace_id, db)
        else:
            new_weather_sensor_record = WeatherSensorModel(
                trace_id=trace_id,
                date_time=invalid_body["utc_timestamp"],
                temperature=invalid_body.get("GB_temperature"),
                radiation_direct_horizontal=invalid_body.get("GB_radiation_direct_horizontal"),
                radiation_diffuse_horizontal=invalid_body.get("GB_radiation_diffuse_horizontal"),
            )
            write_new_record(new_weather_sensor_record, trace_id, db)
    finally:
        db.close()

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({
            "trace_id": trace_id,
            "event": "validation_error",
            "detail": exc.errors(),
            "body": exc.body}),
    )
