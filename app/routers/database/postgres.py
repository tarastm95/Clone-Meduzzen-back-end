from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from sqlalchemy import text

router = APIRouter()


@router.get("/postgres-test")
async def postgres_test(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "connected to PostgreSQL"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
