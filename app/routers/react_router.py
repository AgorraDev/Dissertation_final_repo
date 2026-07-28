from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.database import get_db
from app.schemas.sensor_schemas import WeatherDataTrace, GenerationDataTrace, TraceEventOut
from app.db_models.sensor_models import (
    WeatherData as WeatherModel,
    GenerationData as GenerationModel,
    AnomalyLog as AnomalyModel,
    TraceEvent as TraceEventModel,
)

router = APIRouter()

@router.get("/weather", response_model=List[WeatherDataTrace])
def weather(db: Session = Depends(get_db)):
    query = db.scalars(select(WeatherModel)).all()

    messages = []
    for row in query:
        messages.append({
            "trace_id": row.trace_id,
            "utc_timestamp": row.date_time,
            "GB_temperature": row.temperature or 0.0,
            "GB_radiation_direct_horizontal": row.radiation_direct_horizontal or 0.0,
            "GB_radiation_diffuse_horizontal": row.radiation_diffuse_horizontal or 0.0,
        })
    return messages

@router.get("/generation", response_model=List[GenerationDataTrace])
def generation(db: Session = Depends(get_db)):
    query = db.scalars(select(GenerationModel)).all()

    messages = []
    for row in query:
        messages.append({
            "trace_id": row.trace_id,
            "utc_timestamp": row.date_time,
            "GB_GBN_load_actual_entsoe_transparency": row.load_actual_entsoe_transparency or 0.0,
            "GB_GBN_load_forecast_entsoe_transparency": row.load_forecast_entsoe_transparency or 0.0,
            "GB_GBN_price_day_ahead": row.price_day_ahead or 0.0,
            "GB_GBN_solar_capacity": row.solar_capacity or 0.0,
            "GB_GBN_solar_generation_actual": row.solar_generation_actual or 0.0,
            "GB_GBN_solar_profile": row.solar_profile or 0.0,
        })

    return messages

@router.get("/anomaly_log", response_model=None)
def anomalies(db: Session = Depends(get_db)):
    query = db.scalars(select(AnomalyModel)).all()

    messages = []
    for row in query:
        messages.append({
            "trace_id": row.trace_id,
            "date_time": row.date_time,
            "source": row.source,
            "error_details": row.error_details,
            "error_payload": row.error_payload
        })

    return messages

@router.get("/trace/{trace_id}", response_model=List[TraceEventOut])
def trace_detail(trace_id: str, db: Session = Depends(get_db)):
    events = db.scalars(
        select(TraceEventModel)
        .where(TraceEventModel.trace_id==trace_id)
        .order_by(TraceEventModel.created_at, TraceEventModel.id)
    ).all()

    if not events:
        raise HTTPException(status_code=404, detail=f"No trace events found for {trace_id}")

    return events