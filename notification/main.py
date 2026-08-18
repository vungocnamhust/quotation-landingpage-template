from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from notification.api.v2.events import router as events_router
from notification.api.v2.notifications import router as notifications_router
from notification.api.v2.stream import router as stream_router
from notification.infrastructure.db.base import get_notification_engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("notification-service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Starting Notification Microservice...")
    yield
    log.info("Shutting down Notification Microservice...")
    engine = get_notification_engine()
    await engine.dispose()


app = FastAPI(
    title="Travel.AI Notification Service",
    description="Dedicated microservice for ingesting domain events and delivering real-time multi-tenant notifications.",
    version="2.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "notification-service"}


# Register API routers
app.include_router(events_router)
app.include_router(notifications_router)
app.include_router(stream_router)
