import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

'''
Read env variables (db_secrets etc.)

Use Pydantic BaseSettings
'''

load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "Energy Anomaly Webapp"
    PROJECT_VERSION: str = "0.0.1"

    DATABASE_USER: str = os.getenv("DATABASE_USER")
    DATABASE_PASSWORD: str = os.getenv("DATABASE_PASSWORD")
    DATABASE_SERVER: str = os.getenv("DATABASE_SERVER")
    DATABASE_PORT: str = os.getenv("DATABASE_PORT")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME")
    DATABASE_SCHEMA: str = os.getenv("DATABASE_SCHEMA")

    DATABASE_URL: str = f"postgresql+psycopg2://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_SERVER}:{DATABASE_NAME}?options=-c%20search_path={DATABASE_SCHEMA}"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
