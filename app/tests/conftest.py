import os
import psycopg2
import pytest
from pathlib import Path
from dotenv import dotenv_values
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from app.db_models.sensor_models import TraceEvent
from fastapi.testclient import TestClient
import app.services.trace_events as trace_events_module

# Set up testdb environment details
_env = dotenv_values(Path(__file__).resolve().parents[2] / ".env")

os.environ.update({
    "DATABASE_USER": _env["DATABASE_USER"],
    "DATABASE_PASSWORD": _env["DATABASE_PASSWORD"],
    "DATABASE_SERVER": _env["DATABASE_SERVER"],
    "DATABASE_PORT": _env["DATABASE_PORT"],
    "DATABASE_NAME": _env["DATABASE_NAME"],
    "DATABASE_SCHEMA": "energy_test",
})

# Create testdb schema if they do not exist
def _ensure_test_schema() -> None:
    conn = psycopg2.connect(
        dbname=os.environ["DATABASE_NAME"],
        user=os.environ["DATABASE_USER"],
        password=os.environ["DATABASE_PASSWORD"],
        host=os.environ["DATABASE_SERVER"],
        port=os.environ["DATABASE_PORT"],
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    with conn.cursor() as cur:
        cur.execute(f'CREATE SCHEMA IF NOT EXISTS {os.environ["DATABASE_SCHEMA"]}')
    conn.close()

_ensure_test_schema()

# App imports
from app.db.database import Base, engine, get_db
from app.main import app

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False)

# Fixtures to serve test needs
@pytest.fixture(scope="session", autouse=True)
def tables():
    '''Create all tables for a test run, drop at end to clear up db'''
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()

@pytest.fixture()
def db_session():
    conn = engine.connect()
    transaction = conn.begin()
    session = TestingSessionLocal(
        bind=conn,
        join_transaction_mode="create_savepoint"
    )
    yield session
    session.close()
    transaction.rollback()
    conn.close()

@pytest.fixture()
def client(db_session):
    '''
    for endpoints -> dependency_overrides[get_db
    for exception handler -> app.state.sessionmaker
    '''
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    bind = db_session.get_bind()
    test_audit_factory = lambda: TestingSessionLocal(
        bind=bind,
        join_transaction_mode="create_savepoint"
    )
    original_audit = trace_events_module.AuditSessionLocal
    trace_events_module.AuditSessionLocal = test_audit_factory

    with TestClient(app) as test_client:
        app.state.db_sessionmaker = lambda: db_session
        yield test_client

    trace_events_module.AuditSessionLocal = original_audit
    app.dependency_overrides.clear()

@pytest.fixture()
def audit_factory(db_session):
    bind = db_session.get_bind()
    return lambda: TestingSessionLocal(
        bind=bind,
        join_transaction_mode="create_savepoint"
    )