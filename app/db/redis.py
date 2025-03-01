import redis.asyncio as aioredis
from app.core.config import redis_settings

REDIS_URL = redis_settings.REDIS_URL

redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)


async def get_redis() -> aioredis.Redis:
    return redis_client
