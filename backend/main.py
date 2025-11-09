# FastAPI Backend for Trading Platform (Epic 25)
# Main application entry point

from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from contextlib import asynccontextmanager


# Health check models and router
class HealthResponse(BaseModel):
    """Health check response model"""

    status: str = "ok"


health_router = APIRouter()


@health_router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint for service monitoring.

    Returns:
        HealthResponse: Service health status
    """
    return HealthResponse(status="ok")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup/shutdown events"""
    # Startup
    print("🚀 Starting FastAPI Backend for Trading Platform")

    yield

    # Shutdown
    print("🛑 Shutting down FastAPI Backend")


# Create FastAPI application
app = FastAPI(
    title="AI Trading Backtesting Backend",
    description="FastAPI backend service for managing backtesting, optimization, and analytics workflows",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS for external access (localhost development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router, prefix="/api", tags=["health"])
app.include_router(
    health_router, prefix="", tags=["health"]
)  # Also expose at root for health checks

# Import and include backtest router
from backend.routers.backtests import router as backtest_router

app.include_router(backtest_router, prefix="/api", tags=["backtests"])

# Import and include MLflow router
from backend.routers.mlflow import router as mlflow_router

app.include_router(mlflow_router, prefix="/api", tags=["mlflow"])

# Import and include optimization router
from backend.routers.optimization import router as optimization_router

app.include_router(optimization_router, prefix="/api", tags=["optimization"])

# Import and include analytics router
from backend.routers.analytics import router as analytics_router

app.include_router(analytics_router, prefix="/api", tags=["analytics"])


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "AI Trading Backtesting Backend API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health",
    }


if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app", host="0.0.0.0", port=8000, reload=True, log_level="info"
    )
