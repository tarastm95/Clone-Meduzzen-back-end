from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from app.routers.database import postgres, redis
from app.routers import health, user
from app.core.logger import logger

app = FastAPI(title="Backend API")


@app.on_event("startup")
async def startup_event():
    logger.info("Backend API is starting...")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Backend API is shutting down...")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logger.info(f"Incoming request: {request.method} {request.url}")
        response = await call_next(request)
        logger.info(f"Response status: {response.status_code}")
        return response


app.add_middleware(LoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(redis.router)
app.include_router(postgres.router)
app.include_router(user.router)

logger.info("Backend API has been initialized.")
