from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    database_url: str = Field(alias='DATABASE_URL')
    redis_url: str = Field(alias='REDIS_URL', default='redis://redis:6379/0')

    jwt_secret: str = Field(alias='JWT_SECRET')
    jwt_algorithm: str = Field(alias='JWT_ALGORITHM', default='HS256')
    jwt_expire_minutes: int = Field(alias='JWT_EXPIRE_MINUTES', default=1440)

    log_level: str = Field(alias='LOG_LEVEL', default='INFO')

    api_v1_prefix: str = '/api/v1'


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
