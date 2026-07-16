"""FastAPI application entrypoint.

Only app wiring lives here: middleware, routers, startup/shutdown hooks.
Business logic belongs in `app/services/`; route handlers stay thin and
delegate immediately.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging_config import configure_logging
from app.api.v1 import autocomplete, listings, predict, search, stats, trends

configure_logging()
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title="Lahore Rental Intelligence System",
    description="Rental listing aggregation, normalization, and rent prediction API.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router, prefix=settings.api_v1_prefix)
app.include_router(predict.router, prefix=settings.api_v1_prefix)
app.include_router(autocomplete.router, prefix=settings.api_v1_prefix)
app.include_router(listings.router, prefix=settings.api_v1_prefix)
app.include_router(stats.router, prefix=settings.api_v1_prefix)
app.include_router(trends.router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Liveness/readiness probe.

    Returns:
        A small JSON payload confirming the API process is up and which
        environment it's running in.
    """
    return {"status": "ok", "environment": settings.environment}
