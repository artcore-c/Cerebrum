# cerebrum/api/routes/health.py

"""Health check routes"""
from fastapi import APIRouter
from pydantic import BaseModel
import time
from cerebrum.core.vps_client import get_vps_client

router = APIRouter(tags=["health"])

# Track startup time (will be set by main.py)
startup_time = None

def set_startup_time(t: float):
    global startup_time
    startup_time = t

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    cm4_status: str
    vps_status: str
    vps_available: bool
    uptime_seconds: float

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check both CM4 status and VPS availability"""
    vps = get_vps_client()
    vps_health = await vps.check_health()
    vps_available = vps_health.get("available", False)
    vps_status = "healthy" if vps_available else "unavailable"

    return HealthResponse(
        status="healthy",
        cm4_status="operational",
        vps_status=vps_status,
        vps_available=vps_available,
        uptime_seconds=max(0.0, time.time() - (startup_time if startup_time is not None else time.time()))
    )
