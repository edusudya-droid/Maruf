"""FastAPI asosiy ilovasi."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from backend.api.routers import (
    sources, articles, events, briefs, users, alerts, stats, scheduler_router
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Daily Intelligence System API...")
    yield
    logger.info("Shutting down API...")


app = FastAPI(
    title="Daily Intelligence System API",
    description="300+ manbadan avtomatik ma'lumot yig'ib, AI brifing yaratuvchi tizim",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"
app.include_router(sources.router, prefix=API_PREFIX)
app.include_router(articles.router, prefix=API_PREFIX)
app.include_router(events.router, prefix=API_PREFIX)
app.include_router(briefs.router, prefix=API_PREFIX)
app.include_router(users.router, prefix=API_PREFIX)
app.include_router(alerts.router, prefix=API_PREFIX)
app.include_router(stats.router, prefix=API_PREFIX)
app.include_router(scheduler_router.router, prefix=API_PREFIX)


@app.get("/")
async def root():
    return {"status": "ok", "service": "Daily Intelligence System"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
