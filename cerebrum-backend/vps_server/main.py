# ~/cerebrum-backend/vps_server/main.py

"""
Cerebrum VPS Backend - Lightweight Inference Server
===================================================

Runs heavy model inference on VPS, called by CM4 orchestrator.
Minimal footprint, optimized for speed.

Run: uvicorn vps_server.main:app --host 127.0.0.1 --port 9000
"""

import os
import time
import psutil
from typing import Optional, Dict, Any
from datetime import datetime
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import logging
import json

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('CerebrumVPS')

# Configuration
CEREBRUM_API_KEY = os.getenv("CEREBRUM_API_KEY")
if not CEREBRUM_API_KEY:
    raise RuntimeError("CEREBRUM_API_KEY is not set")
MAX_CPU_PERCENT = float(os.getenv("MAX_CPU_PERCENT", "70"))
ALLOWED_CM4_IP = os.getenv("ALLOWED_CM4_IP", "127.0.0.1")
CEREBRUM_N_THREADS = int(os.getenv("CEREBRUM_N_THREADS", "1"))

# ============================================================================
# SECURITY HELPERS
# ============================================================================

def is_allowed_client(request: Request) -> bool:
    client_ip = request.client.host

    # Always allow local loopback (health checks, local testing)
    if client_ip in ("127.0.0.1", "::1"):
        return True

    # Allow CM4 over Tailscale
    if ALLOWED_CM4_IP and client_ip == ALLOWED_CM4_IP:
        return True

    return False

# Initialize FastAPI
app = FastAPI(
    title="Cerebrum VPS Backend",
    description="High-performance inference backend for Cerebrum AI",
    version="0.1.0"
)

# Global model cache
_model_cache: Dict[str, Any] = {}
_model_last_used: Dict[str, datetime] = {}


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class InferenceRequest(BaseModel):
    """Request for model inference"""
    prompt: str = Field(..., description="Input prompt for the model")
    model: str = Field(..., description="Model name to use")
    max_tokens: int = Field(512, ge=1, le=4096, description="Maximum tokens to generate")
    temperature: float = Field(0.2, ge=0.0, le=2.0, description="Sampling temperature")
    stop: Optional[list[str]] = Field(None, description="Stop sequences")

    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "def fibonacci(n):",
                "model": "qwen_7b",
                "max_tokens": 256,
                "temperature": 0.2
            }
        }


class InferenceResponse(BaseModel):
    """Response from inference"""
    result: str
    model: str
    tokens_generated: int
    inference_time_seconds: float
    timestamp: str


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    available: bool
    cpu_usage_percent: float
    ram_available_gb: float
    ram_used_gb: float
    models_in_cache: list[str]
    uptime_seconds: float


# ============================================================================
# LIGHTWEIGHT MODEL MANAGER
# ============================================================================

class VPSModelEngine:
    """Lightweight model engine for VPS inference"""

    def __init__(self):
        self.models = {}
        self.load_times = {}
        self.inference_count = {}
        self.start_time = time.time()

    def get_cpu_usage(self) -> float:
        """Get current CPU usage"""
        return psutil.cpu_percent(interval=0.1)

    def get_ram_info(self) -> tuple[float, float]:
        """Get RAM info in GB (available, used)"""
        mem = psutil.virtual_memory()
        available = mem.available / (1024**3)
        used = mem.used / (1024**3)
        return available, used

    def can_accept_request(self) -> tuple[bool, str]:
        """Check if VPS can accept new inference request"""
        cpu_usage = self.get_cpu_usage()

        if cpu_usage > MAX_CPU_PERCENT:
            return False, f"CPU usage too high: {cpu_usage:.1f}%"

        available_ram, _ = self.get_ram_info()
        if available_ram < 1.0:  # Less than 1GB available
            return False, f"Insufficient RAM: {available_ram:.2f}GB available"

        return True, "Available"

    def load_model(self, model_name: str) -> Any:
        """Load a model (with caching)"""

        # Check cache
        if model_name in self.models:
            logger.info(f"Model {model_name} loaded from cache")
            self.load_times[model_name] = datetime.now()
            return self.models[model_name]

        # Load model
        logger.info(f"Loading model {model_name}...")
        start = time.time()

        try:
            from llama_cpp import Llama

            # Map model names to file paths
            model_paths = {
                "qwen_7b": "/home/unicorn1/cerebrum-backend/models/qwen-7b-q4.gguf",
                "codellama_7b": "/home/unicorn1/cerebrum-backend/models/codellama-7b-q4.gguf",
                "codellama_13b": "/home/unicorn1/cerebrum-backend/models/codellama-13b-q3.gguf",
                "deepseek_6b": "/home/unicorn1/cerebrum-backend/models/deepseek-6.7b-q4.gguf",
                "wizardcoder_15b": "/home/unicorn1/cerebrum-backend/models/wizardcoder-15b-q2.gguf",
            }

            if model_name not in model_paths:
                raise ValueError(f"Unknown model: {model_name}")

            model_path = model_paths[model_name]

            # Check if model file exists
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Model file not found: {model_path}")

            # Load with llama.cpp
            model = Llama(
                model_path=model_path,
                n_ctx=4096,
                n_threads=CEREBRUM_N_THREADS,  # CRITICAL: force 1 thread on VPS
                n_gpu_layers=0,
                verbose=False
            )

            # Cache it
            self.models[model_name] = model
            self.load_times[model_name] = datetime.now()
            self.inference_count[model_name] = 0

            load_time = time.time() - start
            logger.info(f"Model {model_name} loaded in {load_time:.2f}s")

            return model

        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            raise

    def unload_model(self, model_name: str) -> bool:
        """Unload a model from cache"""
        if model_name in self.models:
            del self.models[model_name]
            logger.info(f"Model {model_name} unloaded from cache")
            return True
        return False

    def cleanup_old_models(self, max_age_minutes: int = 60):
        """Remove models not used recently"""
        now = datetime.now()
        to_remove = []

        for model_name, last_used in self.load_times.items():
            age = (now - last_used).total_seconds() / 60
            if age > max_age_minutes:
                to_remove.append(model_name)

        for model_name in to_remove:
            self.unload_model(model_name)
            logger.info(f"Auto-unloaded {model_name} (inactive for {max_age_minutes}min)")

    def get_uptime(self) -> float:
        """Get server uptime in seconds"""
        return time.time() - self.start_time


# Initialize global engine
vps_engine = VPSModelEngine()


# ============================================================================
# MIDDLEWARE
# ============================================================================

@app.middleware("http")
async def check_capacity(request: Request, call_next):
    """Check if VPS can handle request before processing"""

    # Skip for health checks
    if request.url.path == "/health":
        return await call_next(request)

    # Check capacity
    can_accept, reason = vps_engine.can_accept_request()
    if not can_accept:
        return JSONResponse(
            status_code=503,
            content={
                "error": "VPS overloaded",
                "reason": reason,
                "suggestion": "Fallback to CM4 local inference"
            }
        )

    return await call_next(request)


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/", response_model=dict)
async def root():
    """Root endpoint"""
    return {
        "service": "Cerebrum VPS Backend",
        "version": "0.1.0",
        "status": "operational",
        "endpoints": {
            "inference": "/v1/inference",
            "health": "/health",
            "models": "/v1/models"
        }
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint - no auth required"""

    cpu_usage = vps_engine.get_cpu_usage()
    ram_available, ram_used = vps_engine.get_ram_info()
    can_accept, _ = vps_engine.can_accept_request()

    return HealthResponse(
        status="healthy" if can_accept else "overloaded",
        available=can_accept,
        cpu_usage_percent=cpu_usage,
        ram_available_gb=ram_available,
        ram_used_gb=ram_used,
        models_in_cache=list(vps_engine.models.keys()),
        uptime_seconds=vps_engine.get_uptime()
    )


@app.post("/v1/inference", response_model=InferenceResponse)
async def inference(
    request: InferenceRequest,
    http_request: Request,
    x_api_key: str = Header(None, alias="X-API-Key")
):

    """
    Run inference on a model

    Requires X-API-Key header for authentication
    """

    # Verify API key
    if x_api_key != CEREBRUM_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")

    # Verify client IP (defense-in-depth)
    if not is_allowed_client(http_request):
        raise HTTPException(
            status_code=403,
            detail="Client IP not allowed"
        )

    logger.info(f"Inference request: {request.model} - {len(request.prompt)} chars")


    try:
        # Load model
        model = vps_engine.load_model(request.model)

        # Run inference
        start_time = time.time()

        result = model(
            request.prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            stop=request.stop or [],
            echo=False
        )

        inference_time = time.time() - start_time

        # Extract generated text
        generated_text = result['choices'][0]['text']
        tokens_generated = result['usage']['completion_tokens']

        # Update stats
        vps_engine.inference_count[request.model] = \
            vps_engine.inference_count.get(request.model, 0) + 1

        logger.info(
            f"Inference complete: {tokens_generated} tokens in {inference_time:.2f}s "
            f"({tokens_generated/inference_time:.1f} tokens/s)"
        )

        return InferenceResponse(
            result=generated_text,
            model=request.model,
            tokens_generated=tokens_generated,
            inference_time_seconds=round(inference_time, 3),
            timestamp=datetime.now().isoformat()
        )

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Model not found: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Inference error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Inference failed: {str(e)}"
        )

@app.post("/v1/inference/stream")
async def inference_stream(
    request: InferenceRequest,
    http_request: Request,
    x_api_key: str = Header(None, alias="X-API-Key")
):
    """
    Stream inference tokens as they're generated
    
    Returns Server-Sent Events (SSE) stream
    """
    
    # Same auth as regular inference
    if x_api_key != CEREBRUM_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    if not is_allowed_client(http_request):
        raise HTTPException(status_code=403, detail="Client IP not allowed")
    
    logger.info(f"Streaming inference request: {request.model} - {len(request.prompt)} chars")
    
    async def generate():
        try:
            # Load model
            model = vps_engine.load_model(request.model)
            
            start_time = time.time()
            total_tokens = 0
            
            # Stream tokens
            for chunk in model(
                request.prompt,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                stop=request.stop or [],
                echo=False,
                stream=True  # Enable streaming
            ):
                # Extract token from chunk
                token = chunk['choices'][0]['text']
                total_tokens += 1
                
                # Send as SSE
                data = {
                    "token": token,
                    "total_tokens": total_tokens
                }
                yield f"data: {json.dumps(data)}\n\n"
            
            # Send completion event
            inference_time = time.time() - start_time
            completion = {
                "done": True,
                "total_tokens": total_tokens,
                "inference_time": round(inference_time, 3),
                "tokens_per_second": round(total_tokens / inference_time, 2)
            }
            yield f"data: {json.dumps(completion)}\n\n"
            
            # Update stats
            vps_engine.inference_count[request.model] = \
                vps_engine.inference_count.get(request.model, 0) + 1
            
            logger.info(f"Streaming complete: {total_tokens} tokens in {inference_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            error = {"error": str(e), "done": True}
            yield f"data: {json.dumps(error)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )

@app.get("/v1/models")
async def list_models(x_api_key: str = Header(None, alias="X-API-Key")):
    """List available models"""

    if x_api_key != CEREBRUM_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")

    return {
        "available_models": [
            "qwen_7b",
            "codellama_7b",
            "codellama_13b",
            "deepseek_6b",
            "wizardcoder_15b"
        ],
        "cached_models": list(vps_engine.models.keys()),
        "inference_counts": vps_engine.inference_count
    }


@app.post("/v1/unload/{model_name}")
async def unload_model(
    model_name: str,
    x_api_key: str = Header(None, alias="X-API-Key")
):
    """Manually unload a model from cache"""

    if x_api_key != CEREBRUM_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")

    success = vps_engine.unload_model(model_name)

    if success:
        return {"status": "unloaded", "model": model_name}
    else:
        raise HTTPException(status_code=404, detail="Model not in cache")


@app.post("/v1/cleanup")
async def cleanup_cache(x_api_key: str = Header(None, alias="X-API-Key")):
    """Clean up old models from cache"""

    if x_api_key != CEREBRUM_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")

    before = len(vps_engine.models)
    vps_engine.cleanup_old_models(max_age_minutes=30)
    after = len(vps_engine.models)

    return {
        "status": "cleaned",
        "models_removed": before - after,
        "models_remaining": after
    }


@app.get("/v1/stats")
async def get_stats(x_api_key: str = Header(None, alias="X-API-Key")):
    """Get detailed statistics"""

    if x_api_key != CEREBRUM_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")

    cpu_usage = vps_engine.get_cpu_usage()
    ram_available, ram_used = vps_engine.get_ram_info()

    return {
        "system": {
            "cpu_usage_percent": cpu_usage,
            "ram_available_gb": ram_available,
            "ram_used_gb": ram_used,
            "uptime_seconds": vps_engine.get_uptime()
        },
        "models": {
            "cached": list(vps_engine.models.keys()),
            "count": len(vps_engine.models),
            "inference_counts": vps_engine.inference_count,
            "last_used": {
                name: time.isoformat()
                for name, time in vps_engine.load_times.items()
            }
        }
    }


# ============================================================================
# STARTUP/SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Run on server startup"""
    logger.info("=" * 60)
    logger.info("Cerebrum VPS Backend starting...")
    logger.info(f"API Key configured: {'Yes' if CEREBRUM_API_KEY else 'NO - INSECURE!'}")
    logger.info(f"Max CPU threshold: {MAX_CPU_PERCENT}%")
    logger.info(f"Allowed CM4 IP: {ALLOWED_CM4_IP}")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Run on server shutdown"""
    logger.info("Cerebrum VPS Backend shutting down...")
    # Models will be garbage collected automatically


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    # Get bind IP from env or default to Tailscale IP
    bind_ip = os.getenv("VPS_BIND_IP", "127.0.0.1")
    bind_port = int(os.getenv("CEREBRUM_VPS_PORT", "9000"))

    logger.info(f"Starting server on {bind_ip}:{bind_port}")

    uvicorn.run(
        app,
        host=bind_ip,
        port=bind_port,
        log_level="info"
    )
