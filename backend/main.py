"""
V2 Parallel Optimization System - FastAPI Backend
Provides REST API for parallel strategy optimization with real-time monitoring.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import logging
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events."""
    logger.info("Starting V2 Optimization Backend")
    yield
    logger.info("Shutting down V2 Optimization Backend")


# Create FastAPI application
app = FastAPI(
    title="V2 Parallel Optimization API",
    description="REST API for parallel strategy optimization with real-time monitoring",
    version="2.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "v2-optimization-backend"}


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "V2 Parallel Optimization System API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health",
    }


# Import and include routers
try:
    from backend.routers.optimization import router as optimization_router

    app.include_router(
        optimization_router, prefix="/api/optimization", tags=["optimization"]
    )

    logger.info("Optimization router loaded successfully")

except ImportError as e:
    logger.error(f"Failed to load optimization router: {e}")
    # Continue without routers for health checks during development
