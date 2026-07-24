from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from urllib.parse import quote_plus
class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    APP_NAME: str = Field(...)
    APP_VERSION: str = Field(...)
    APP_ENV: str = Field(...)
    DEBUG: bool = Field(default=False)

    # PostgreSQL
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str

    # MySQL
    MYSQL_HOST: str
    MYSQL_PORT: int
    MYSQL_DB: str
    MYSQL_USER: str
    MYSQL_PASSWORD: str

    # Scheduler
    SYNC_INTERVAL_MINUTES: int = 2

    # AWS
    AWS_ACCESS_KEY: str = ""
    AWS_SECRET_KEY: str = ""
    AWS_BUCKET_NAME: str = ""
    AWS_REGION: str = ""

    # Groq
    GROQ_API_KEY: str = ""
    
    MYSQL_TIMEZONE: str = "Asia/Kolkata"
    
    # Embedding
    
    EMBEDDING_MODEL_NAME: str =""
    EMBEDDINGS_DIMENSIONS: int = 384
    
    GROQ_BATCH_DELAY_SECONDS: float
    
    SKILLS_WEIGHT: float
    EXPERIENCE_WEIGHT: float
    EDUCATION_WEIGHT: float
    LOCATION_WEIGHT: float

    @property
    def postgres_url(self) -> str:
        return (
            f"postgresql+asyncpg://"
            f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}"
            f"/{self.POSTGRES_DB}"
        )

    @property
    def mysql_url(self) -> str:
        password = quote_plus(self.MYSQL_PASSWORD)

        return (
            f"mysql+aiomysql://"
            f"{self.MYSQL_USER}:{password}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}"
            f"/{self.MYSQL_DB}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()