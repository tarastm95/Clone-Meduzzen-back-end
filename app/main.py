from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from app.routers.database import postgres, redis
from app.routers import health, user, auth0, auth, company, company_actions, owned_companies
from app.core.logger import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Backend API is starting...")
    yield
    logger.info("Backend API is shutting down...")

app = FastAPI(title="Backend API", lifespan=lifespan)

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logger.info(f"Incoming request: {request.method} {request.url}")
        response = await call_next(request)
        logger.info(f"Response status: {response.status_code}")
        return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LoggingMiddleware)

# Мапа HTTP статусів до ключів перекладу
error_keys = {
    400: "error.badRequest",
    401: "error.unauthorized",
    403: "error.forbidden",
    404: "error.notFound",
    500: "error.serverError"
}

# Кастомний обробник HTTPException
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    error_key = error_keys.get(exc.status_code, "error.unknown")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "key": error_key,
                "message": exc.detail if exc.detail else "An error occurred"
            }
        }
    )

app.include_router(health.router)
app.include_router(redis.router)
app.include_router(postgres.router)
app.include_router(user.router)
app.include_router(auth0.router)
app.include_router(auth.router)
app.include_router(company.router)
app.include_router(company_actions.router)
app.include_router(owned_companies.router)

logger.info("Backend API has been initialized.")
