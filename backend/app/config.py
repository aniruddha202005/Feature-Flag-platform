from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://flags:flags@localhost:5432/flags"
    redis_url: str = "redis://localhost:6379/0"

    flag_cache_ttl_seconds: int = 300
    eval_cache_ttl_seconds: int = 60
    negative_cache_ttl_seconds: int = 10

    redis_socket_timeout_seconds: float = 0.25
    redis_cooldown_seconds: float = 5.0

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]


settings = Settings()
