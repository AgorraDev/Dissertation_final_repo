import logging
from uuid import uuid4
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.schemas.sensor_schemas import WeatherData, GenerationData
from app.db.database import get_db
from app.services.ingest_success import ingest_success
from app.services.trace_events import emit_trace_events, STAGE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("IngestionLogger")
router = APIRouter()

@router.post("/ingest/generation")
def ingest_generation_data(plant_data: GenerationData, db: Session = Depends(get_db)):
    trace_id = str(uuid4())
    # Pydantic has already validated any incoming data by this point with @exceptionhandler
    # Endpoint can assert we have validated and received row which are seperated for trace_events
    emit_trace_events(trace_id, STAGE.RECEIVED, source="generation_data")
    emit_trace_events(trace_id, STAGE.VALIDATED, source="generation_data")
    is_written = ingest_success(plant_data, "generation_data", trace_id, db)
    return {"trace_id": trace_id, "status": "persisted" if is_written else "duplicate_rejected"}

@router.post("/ingest/weather")
def ingest_weather_data(plant_data: WeatherData, db: Session = Depends(get_db)):
    trace_id = str(uuid4())
    emit_trace_events(trace_id, STAGE.RECEIVED, source="weather_data")
    emit_trace_events(trace_id, STAGE.VALIDATED, source="weather_data")
    is_written = ingest_success(plant_data, "weather_data", trace_id, db)
    return {"trace_id": trace_id, "status": "persisted" if is_written else "invalid_request"}
