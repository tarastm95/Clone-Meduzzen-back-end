from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.database import postgres, redis
from app.routers import health, user

app = FastAPI(title="Meduzzen-back-end")

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
