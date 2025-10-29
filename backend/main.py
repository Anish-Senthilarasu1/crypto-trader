"""
Aurora Trader - Main FastAPI Application

Production-ready paper trading system with web UI.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from backend.api import control, health, metrics


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager for startup and shutdown events.

    Args:
        app: FastAPI application instance

    Yields:
        None during application lifetime
    """
    # Startup
    logger.info("🚀 Aurora Trader starting up...")
    logger.info("Environment: Paper Trading Mode")

    yield

    # Shutdown
    logger.info("🛑 Aurora Trader shutting down...")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title="Aurora Trader API",
        description="Production-ready paper trading system",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    app.include_router(health.router, tags=["health"])
    app.include_router(metrics.router, prefix="/api", tags=["metrics"])
    app.include_router(control.router, prefix="/api", tags=["control"])

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
