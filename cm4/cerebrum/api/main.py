"""
Cerebrum CM4 Main API Server
============================

FastAPI server running on CM4 that orchestrates requests
between local processing and VPS backend.

File: /opt/cerebrum/cerebrum/api/main.py

Run: uvicorn cerebrum.api.main:app --host 0.0.0.0 --port 7000
"""

import os
import time
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Import our VPS client
import sys
sys.path.insert(0, '/opt/cerebrum')
from cerebrum.core.vps_client import (
    VPSClient,
    VPSUnavailableError,
    VPSInferenceError,
    get_vps_client
)

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

# Global VPS client
vps_client: Optional[VPSClient] = None


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class CodeCompletionRequest(BaseModel):
    """Request for code completion"""
    prompt: str = Field(..., description="Code context/prompt")
    language: str = Field("python", description="Programming language")
    max_tokens: int = Field(512, ge=1, le=2048)
    temperature: float = Field(0.2, ge=0.0, le=2.0)

    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "def fibonacci(n):",
                "language": "python",
                "max_tokens": 256,
                "temperature": 0.2
            }
        }


class CodeCompletionResponse(BaseModel):
    """Response from code completion"""
    result: str
    language: str
    source: str  # "vps" or "local"
    model_used: str
    tokens_generated: int
    inference_time_seconds: float
    timestamp: str


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    cm4_status: str
    vps_status: str
    vps_available: bool
    uptime_seconds: float


# ============================================================================
# STARTUP/SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    global vps_client

    logger.info("=" * 60)
    logger.info("Cerebrum CM4 Orchestrator starting...")
    logger.info(f"VPS Endpoint: {os.getenv('VPS_ENDPOINT', 
'http://100.78.22.113:9000')}")
    logger.info("=" * 60)

    # Initialize VPS client
    vps_client = get_vps_client()

    # Test VPS connection
    try:
        health = await vps_client.check_health()
        if health.get("available"):
            logger.info("✓ VPS backend is available")
        else:
            logger.warning("⚠ VPS backend is not available - will use fallback")
    except Exception as e:
        logger.warning(f"⚠ Could not connect to VPS: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Cerebrum CM4 Orchestrator shutting down...")


# ============================================================================
# ROUTES
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
            "stats": "/v1/stats"
        }
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    Checks both CM4 status and VPS availability.
    """
    # Check VPS
    vps_health = await vps_client.check_health()
    vps_available = vps_health.get("available", False)
    vps_status = "healthy" if vps_available else "unavailable"

    return HealthResponse(
        status="healthy",
        cm4_status="operational",
        vps_status=vps_status,
        vps_available=vps_available,
        uptime_seconds=time.time() - startup_time
    )


@app.post("/v1/complete", response_model=CodeCompletionResponse)
async def code_completion(request: CodeCompletionRequest):
    """
    Code completion endpoint.

    Routes to VPS for inference, with fallback handling.
    """
    logger.info(f"Code completion request: {request.language} ({len(request.prompt)} 
chars)")

    start_time = time.time()

    # Determine model based on language
    model_map = {
        "python": "qwen_7b",
        "javascript": "qwen_7b",
        "typescript": "qwen_7b",
        "rust": "codellama_7b",
        "go": "codellama_7b",
        "c": "codellama_7b",
        "cpp": "codellama_7b",
    }

    model = model_map.get(request.language.lower(), "qwen_7b")

    # Try VPS inference
    try:
        result = await vps_client.inference(
            prompt=request.prompt,
            model=model,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )

        inference_time = time.time() - start_time

        return CodeCompletionResponse(
            result=result["result"],
            language=request.language,
            source="vps",
            model_used=result["model"],
            tokens_generated=result["tokens_generated"],
            inference_time_seconds=round(inference_time, 3),
            timestamp=datetime.now().isoformat()
        )

    except VPSUnavailableError as e:
        logger.warning(f"VPS unavailable: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "error": "VPS backend unavailable",
                "message": str(e),
                "suggestion": "VPS may be overloaded or offline"
            }
        )

    except VPSInferenceError as e:
        logger.error(f"VPS inference error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Inference failed",
                "message": str(e)
            }
        )

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "message": str(e)
            }
        )


@app.get("/v1/models")
async def list_models():
    """
    List available models.
    Returns models from VPS backend.
    """
    try:
        vps_models = await vps_client.list_models()
        return {
            "vps_models": vps_models.get("available_models", []),
            "vps_cached": vps_models.get("cached_models", [])
        }
    except Exception as e:
        return {
            "error": str(e),
            "vps_models": []
        }


@app.get("/v1/stats")
async def get_stats():
    """
    Get comprehensive statistics.
    Includes both CM4 and VPS stats.
    """
    # Get VPS stats
    try:
        vps_stats = await vps_client.get_stats()
    except Exception as e:
        vps_stats = {"error": str(e)}

    # Get client stats
    client_stats = vps_client.get_client_stats()

    return {
        "cm4": {
            "uptime_seconds": time.time() - startup_time,
            "vps_client": client_stats
        },
        "vps": vps_stats
    }


@app.post("/v1/vps/health")
async def vps_health():
    """
    Check VPS health status.
    Useful for monitoring.
    """
    try:
        health = await vps_client.check_health()
        return health
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "available": False
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
# GLOBAL VARIABLES
# ============================================================================

startup_time = time.time()


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
