from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "hellotherelogs"
    wcl_client_id: str = ""
    wcl_client_secret: str = ""
    wcl_token_url: str = "https://www.warcraftlogs.com/oauth/token"
    wcl_graphql_url: str = "https://fresh.warcraftlogs.com/api/v2/client"
    database_url: str = "sqlite:///./data/hellotherelogs.sqlite3"
    cache_ttl_seconds: int = 900
    frontend_origin: str = "http://localhost:8080"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
