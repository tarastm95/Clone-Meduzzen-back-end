import pytest
import asyncpg
import redis.asyncio as redis
from app.core.config import db_settings, redis_settings

POSTGRES_CONFIG = {
    "user": db_settings.POSTGRES_USER,
    "password": db_settings.POSTGRES_PASSWORD,
    "database": db_settings.POSTGRES_DB,
    "host": db_settings.POSTGRES_HOST,
    "port": db_settings.DB_PORT,
}

REDIS_CONFIG = {
    "host": redis_settings.REDIS_HOST,
    "port": redis_settings.REDIS_PORT,
    "db": redis_settings.REDIS_DB,
}


@pytest.mark.asyncio
async def test_postgres_connection():
    try:
        conn = await asyncpg.connect(**POSTGRES_CONFIG)
        await conn.close()
    except Exception as e:
        assert False, f"Failed to connect to PostgreSQL: {e}"


@pytest.mark.asyncio
async def test_redis_connection():
    try:
        redis_conn = redis.Redis(
            host=REDIS_CONFIG["host"], port=REDIS_CONFIG["port"], db=REDIS_CONFIG["db"]
        )
        await redis_conn.ping()
        await redis_conn.close()
    except Exception as e:
        assert False, f"Failed to connect to Redis: {e}"


@pytest.mark.asyncio
async def test_connections():
    await test_redis_connection()
    await test_postgres_connection()
