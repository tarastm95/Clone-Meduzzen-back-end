from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class AppSettings(BaseSettings):
    APP_NAME: str = Field(default="Meduzzen-back-end")
    DEBUG: bool = Field(default=True)

    model_config = SettingsConfigDict(env_file=".env", extra="allow")


class DatabaseSettings(BaseSettings):
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    DB_PORT: int

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:"
            f"{self.DB_PORT}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(env_file=".env", extra="allow")


class RedisSettings(BaseSettings):
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    model_config = SettingsConfigDict(env_file=".env", extra="allow")


app_settings = AppSettings()
db_settings = DatabaseSettings()
redis_settings = RedisSettings()
