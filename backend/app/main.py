from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog
import time

from app.core.config import settings
from app.api import (
    market,
    options,
    indicators,
    scanner,
    journal,
    strategies,
    ai,
    risk,
    alerts,
    auth,
    decision_signals,
    agent_analysis,
)

# Configure structured logging
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("application_startup", environment=settings.ENVIRONMENT)

    # Initialize services
    # await initialize_services()

    yield

    logger.info("application_shutdown")
    # await cleanup_services()


app = FastAPI(
    title="AI Trading Assistant API",
    description="AI-powered market analysis and educational insights for NSE markets",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests"""
    start_time = time.time()

    logger.info(
        "request_started",
        method=request.method,
        path=request.url.path,
        client=request.client.host if request.client else None,
    )

    try:
        response = await call_next(request)

        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)

        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            process_time=process_time,
        )

        return response
    except Exception as e:
        logger.error(
            "request_failed",
            method=request.method,
            path=request.url.path,
            error=str(e),
        )
        raise


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        error=str(exc),
        error_type=type(exc).__name__,
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected error occurred",
            "error": type(exc).__name__,
        },
    )


# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(market.router, prefix="/api/v1/market", tags=["Market Data"])
app.include_router(options.router, prefix="/api/v1/options", tags=["Options"])
app.include_router(indicators.router, prefix="/api/v1/indicators", tags=["Indicators"])
app.include_router(scanner.router, prefix="/api/v1/scanner", tags=["Scanner"])
app.include_router(journal.router, prefix="/api/v1/journal", tags=["Journal"])
app.include_router(strategies.router, prefix="/api/v1/strategies", tags=["Strategies"])
app.include_router(ai.router, prefix="/api/v1/ai", tags=["AI Engine"])
app.include_router(risk.router, prefix="/api/v1/risk", tags=["Risk Management"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["Alerts"])
app.include_router(
    decision_signals.router,
    prefix="/api/v1/decision-signals",
    tags=["Decision Signals"],
)
app.include_router(
    agent_analysis.router,
    prefix="/api/v1/agent-analysis",
    tags=["Agent Analysis"],
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "AI Trading Assistant API",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "timestamp": time.time(),
    }
