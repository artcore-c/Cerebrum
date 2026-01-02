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

def format_uptime(seconds: float) -> str:
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours}h {minutes}m"

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    cm4_status: str
    vps_status: str
    vps_available: bool
    
    # NEW (GUI-facing)
    vps_connected: bool
    active_count: int
    queue_count: int
    uptime_seconds: float
    uptime_text: str

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check both CM4 status and VPS availability"""
    vps = get_vps_client()
    vps_health = await vps.check_health()
    vps_available = vps_health.get("available", False)
    vps_status = "healthy" if vps_available else "unavailable"
    
    now = time.time()
    uptime = max(
        0.0,
        now - (startup_time if startup_time is not None else now)
    )
    
    # Minimal, truthful metrics for now
    active_count = 1 if vps_available else 0
    queue_count = 0
    
    return HealthResponse(
        status="healthy",
        cm4_status="operational",
        vps_status=vps_status,
        vps_available=vps_available,
        
        # GUI fields
        vps_connected=vps_available,
        active_count=active_count,
        queue_count=queue_count,
        uptime_seconds=uptime,
        uptime_text=format_uptime(uptime),
    )

