import logging
from contextlib import asynccontextmanager
from sqlalchemy.exc import OperationalError

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

from app.db.database import engine, SessionLocal, AuditSessionLocal
from app.db_models import sensor_models

from app.routers import sensor_ingestion, react_router
from app.services.ingest_failures import ingest_failures

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SystemLog")

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

    app.state.db_sessionmaker = SessionLocal
    app.state.audit_sessionmaker = AuditSessionLocal

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
    source = "generation_data" if "generation" in request.url.path else "weather_data"
    errors = jsonable_encoder(exc.errors())

    # Open session, try to write to Anomaly Log table, then close session
    # Get Session from app.state - this allows us to test exception handler without writing to real db
    db = request.app.state.db_sessionmaker()
    try:
        trace_id = ingest_failures(exc.body, errors, source, db)
    except OperationalError as e:
        logger.error(f"Failed to ingest failures: {e}")
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
