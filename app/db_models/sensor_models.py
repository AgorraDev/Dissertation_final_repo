from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    ForeignKey,
    DateTime,
    UUID,
    JSON,
    Enum)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.db.database import Base
'''
Define database tables for SQLAlchemy models.
'''

'''
ENUMS FOR MAINTAINING STRICT OPTIONS
'''
class RESOLUTION_STATUS(StrEnum):

    NON_ISSUE = "NON_ISSUE"
    FIXED = "FIXED"
    NEEDS_ATTENTION = "NEEDS_ATTENTION"

class USER_ROLE(StrEnum):

    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    ENGINEER = "ENGINEER"
    ANALYST = "ANALYST"

'''
SENSOR DATA TABLES
'''
class GenerationData(Base):
    __tablename__ = "generation_data"
    id = Column(Integer, primary_key=True, index=True)
    trace_id = Column(String, index=True, nullable=False)
    date_time = Column(DateTime, index=True, unique=True, nullable=False)
    load_actual_entsoe_transparency = Column(Float)
    load_forecast_entsoe_transparency = Column(Float)
    price_day_ahead = Column(Float)
    solar_capacity = Column(Float)
    solar_generation_actual = Column(Float)
    solar_profile = Column(Float)


class WeatherData(Base):
    __tablename__ = "weather_data"
    id = Column(Integer, primary_key=True, index=True)
    trace_id = Column(String, index=True, nullable=False)
    date_time = Column(DateTime, index=True, unique=True, nullable=False)
    temperature = Column(Float)
    radiation_direct_horizontal = Column(Float)
    radiation_diffuse_horizontal = Column(Float)

'''
LOGGING + AUDIT TABLES
'''

class TraceEvent(Base):
    __tablename__ = "trace_events"
    id = Column(Integer, primary_key=True, index=True)
    trace_id = Column(String, index=True, nullable=False)
    stage = Column(String, nullable=False)
    status = Column(String, nullable=False)
    source = Column(String)
    details = Column(JSONB)
    # lambda function to call datetime.now on each insert rather than once at model creation
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

class AnomalyLog(Base):
    __tablename__ = "anomaly_log"
    id = Column(Integer, primary_key=True, index=True)
    trace_id = Column(String, index=True, unique=True)
    date_time = Column(DateTime, index=True)
    source = Column(String, index=True, nullable=False)
    error_details = Column(JSON, nullable=False)
    error_payload = Column(JSON, nullable=False)

    actions = relationship("AnomalyActionLog", back_populates='anomaly')

class AnomalyActionLog(Base):
    __tablename__ = "anomaly_action_log"
    id = Column(Integer, primary_key=True, index=True)
    anomaly_trace_id = Column(String, ForeignKey('anomaly_log.trace_id') ,index=True, nullable=False)
    user_id = Column(ForeignKey('facility_users.emp_id'), index=True, nullable=False)
    action_taken = Column(String, nullable=False)
    action_timestamp = Column(DateTime, nullable=False)

    resolution = Column(Enum(RESOLUTION_STATUS, native_enum=False, length=50), nullable=False)
    user = relationship("FacilityUser", back_populates="actions")
    anomaly = relationship("AnomalyLog", back_populates="actions")

'''
USER TABLES
'''
class FacilityUser(Base):
    __tablename__ = "facility_users"
    emp_id = Column(Integer, primary_key=True, index=True)
    emp_name = Column(String, nullable=False, unique=True)
    role = Column(Enum(USER_ROLE, native_enum=False, length=20), nullable=False)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)

    actions = relationship("AnomalyActionLog", back_populates="user")