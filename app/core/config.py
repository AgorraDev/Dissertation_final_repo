from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

'''
Read env variables (db_secrets etc.)    
Use Pydantic BaseSettings
'''
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

class Settings(BaseSettings):
    PROJECT_NAME: str = "Energy Anomaly Webapp"
    PROJECT_VERSION: str = "0.0.1"

    REDIS_URL: str

    DATABASE_USER: str
    DATABASE_PASSWORD: str
    DATABASE_SERVER: str
    DATABASE_PORT: str
    DATABASE_NAME: str
    DATABASE_SCHEMA: str

    @property
    def DATABASE_URL(self) -> str:
        return  (
            f"postgresql+psycopg2://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
            f"@{self.DATABASE_SERVER}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
            f"?options=-c%20search_path={self.DATABASE_SCHEMA}"
                 )

    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore",)

settings = Settings()
