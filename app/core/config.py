from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional


class AppSettings(BaseSettings):
    APP_NAME: str = Field(
        default="Meduzzen-back-end", json_schema_extra={"env": "APP_NAME"}
    )
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

    @property
    def DATABASE_URL_SYNC(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:"
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


class Auth0Settings(BaseSettings):
    AUTH0_DOMAIN: str
    AUTH0_CLIENT_ID: str
    AUTH0_CLIENT_SECRET: str
    AUTH0_AUDIENCE: str = ""
    AUTH0_REDIRECT_URI: str = "http://localhost:8000/auth0/token"

    @property
    def AUTH0_AUTHORIZATION_ENDPOINT(self) -> str:
        return f"https://{self.AUTH0_DOMAIN}/authorize"

    @property
    def AUTH0_TOKEN_ENDPOINT(self) -> str:
        return f"https://{self.AUTH0_DOMAIN}/oauth/token"

    @property
    def AUTH0_JWKS_ENDPOINT(self) -> str:
        return f"https://{self.AUTH0_DOMAIN}/.well-known/jwks.json"

    model_config = SettingsConfigDict(env_file=".env", extra="allow")


class SecuritySettings(BaseSettings):
    JWT_SECRET_KEY: str = Field(..., json_schema_extra={"env": "JWT_SECRET_KEY"})
    JWT_ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)

    model_config = SettingsConfigDict(env_file=".env", extra="allow")


app_settings = AppSettings()
db_settings = DatabaseSettings()
redis_settings = RedisSettings()
auth0_settings = Auth0Settings()
security_settings = SecuritySettings()
