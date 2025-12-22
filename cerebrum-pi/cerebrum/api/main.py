"""
Cerebrum CM4 Main API Server
============================

FastAPI server running on CM4 that orchestrates requests
between local processing and VPS backend.

File: /opt/cerebrum-pi/cerebrum/api/main.py

Run: uvicorn cerebrum.api.main:app --host 0.0.0.0 --port 7000
"""

import os
import time
import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Import middleware
from cerebrum.api.middleware.request_id import RequestIDMiddleware
from cerebrum.api.middleware.log_context import LogContextMiddleware
from cerebrum.api.middleware.load_shed import LoadSheddingMiddleware

# Import route modules
from cerebrum.api.routes import health, inference, models, stats
from cerebrum.core.vps_client import get_vps_client

# Load environment
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('CerebrumCM4')

# Initialize FastAPI
app = FastAPI(
    title="Cerebrum AI - CM4 Orchestrator",
    description="Intelligent code generation and reasoning system",
    version="0.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middleware (registered in reverse execution order)
app.add_middleware(LogContextMiddleware)  # Runs last (logs everything)
app.add_middleware(LoadSheddingMiddleware, max_inflight=2)  # Runs second (rejects overload)
app.add_middleware(RequestIDMiddleware)  # Runs first (generates ID)

# Include routers
app.include_router(health.router)
app.include_router(inference.router)
app.include_router(models.router)
app.include_router(stats.router)

# Track startup time
startup_time = time.time()


# ============================================================================
# STARTUP/SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    global startup_time
    startup_time = time.time()
    
    # Share startup time with route modules
    health.set_startup_time(startup_time)
    stats.set_startup_time(startup_time)

    logger.info("=" * 60)
    logger.info("Cerebrum CM4 Orchestrator starting...")
    logger.info(f"VPS Endpoint: {os.getenv('VPS_ENDPOINT', 'http://127.0.0.1:9000')}")
    logger.info("=" * 60)

    # Initialize VPS client
    vps = get_vps_client()

    # Test VPS connection
    try:
        health_check = await vps.check_health()
        if health_check.get("available"):
            logger.info("✓ VPS backend is available")
        else:
            logger.warning("⚠ VPS backend is not available - will use fallback")
    except Exception as e:
        logger.warning(f"⚠ Could not connect to VPS: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Cerebrum CM4 Orchestrator shutting down...")

    # Clean up VPS client
    vps = get_vps_client()
    await vps.aclose()

# ============================================================================
# ROOT ENDPOINT
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Cerebrum AI - CM4 Orchestrator",
        "version": "0.1.0",
        "status": "operational",
        "endpoints": {
            "health": "/health",
            "code_completion": "/v1/complete",
            "models": "/v1/models",
            "stats": "/v1/stats"
        }
    }


# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "path": str(request.url)
        }
    )


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    # Get configuration from environment
    host = os.getenv("CEREBRUM_HOST", "0.0.0.0")
    port = int(os.getenv("CEREBRUM_PORT", "7000"))

    logger.info(f"Starting Cerebrum CM4 on {host}:{port}")

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )
