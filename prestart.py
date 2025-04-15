import asyncio
import logging
import time
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.sql import text
from app.core.config import db_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def check_db(retries: int = 5, delay: int = 2):
    """Checks database availability before starting the application."""
    engine = create_async_engine(db_settings.DATABASE_URL, echo=False)

    for attempt in range(retries):
        try:
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("✅ Database is ready!")
            return
        except OperationalError:
            logger.warning(f"⏳ Database is not ready yet, retrying in {delay} sec...")
            time.sleep(delay)

    logger.error("❌ Database is unavailable after multiple attempts.")
    raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(check_db())
