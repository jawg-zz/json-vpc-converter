from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "change-me-to-a-random-string"
    database_url: str | None = None
    redis_url: str | None = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
