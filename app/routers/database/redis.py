from fastapi import APIRouter, Depends, HTTPException
from redis.asyncio import Redis
from app.db.redis import get_redis

router = APIRouter()


@router.get("/redis-test")
async def redis_test(redis: Redis = Depends(get_redis)):
    try:
        await redis.ping()
        return {"status": "connected to Redis"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
