import logging
from typing import Any
from datetime import datetime
from pydantic import BaseModel, field_validator, Field

'''
Define data structures here for keeping strict types.
Helps keep backend data passing robust.
'''

logger = logging.getLogger("Schema Log")

# Create BaseModels to force data structure

'''
INCOMING DATA FROM DATA STREAM
'''
class WeatherData(BaseModel):
    utc_timestamp: datetime
    GB_temperature: float
    GB_radiation_direct_horizontal: float = Field(ge=0.0)
    GB_radiation_diffuse_horizontal: float = Field(ge=0.0)

    model_config = {"from_attributes": True}

    @field_validator('utc_timestamp', mode='before')
    @classmethod
    def validate_date_time(cls, value):
        if isinstance(value, str):
            timestamp = value.split("T")
            new_timestamp = timestamp[0] + " " + timestamp[1].split("Z")[0]
            return new_timestamp
        return value

class GenerationData(BaseModel):
    utc_timestamp: datetime
    GB_GBN_load_actual_entsoe_transparency: float = Field(ge=0.0)
    GB_GBN_load_forecast_entsoe_transparency: float = Field(ge=0.0)
    GB_GBN_price_day_ahead: float
    GB_GBN_solar_capacity: float = Field(ge=0.0)
    GB_GBN_solar_generation_actual: float = Field(ge=0.0)
    GB_GBN_solar_profile:  float = Field(ge=0.0)

    model_config = {"from_attributes": True}
    @field_validator('utc_timestamp', mode='before')
    @classmethod
    def validate_date_time(cls, value):
        if isinstance(value, str):
            timestamp = value.split("T")
            new_timestamp = timestamp[0] + " " + timestamp[1].split("Z")[0]
            return new_timestamp
        return value

'''
TRACABILITY MODELS - seperated for security
'''
class WeatherDataTrace(WeatherData):
    trace_id: str

class GenerationDataTrace(GenerationData):
    trace_id: str

'''
FRONTEND MODELS
'''

class TraceEventOut(BaseModel):
    stage: str
    status: str
    source: str | None
    details: Any = None
    created_at: datetime

    model_config = {"from_attributes": True}