# cerebrum/api/routes/stats.py

"""Statistics routes"""
from fastapi import APIRouter
import time
from cerebrum.core.vps_client import get_vps_client

router = APIRouter(tags=["stats"])

# Track startup time (will be set by main.py)
startup_time = None

def set_startup_time(t: float):
    global startup_time
    startup_time = t

@router.get("/v1/stats")
async def get_stats():
    """Get comprehensive CM4 and VPS statistics"""
    vps = get_vps_client()
    
    # Get VPS stats
    try:
        vps_stats = await vps.get_stats()
    except Exception as e:
        vps_stats = {"error": str(e)}
    
    # Get client stats
    client_stats = vps.get_client_stats()
    
    return {
        "cm4": {
            "uptime_seconds": time.time() - (startup_time or time.time()),
            "vps_client": client_stats
        },
        "vps": vps_stats
    }

@router.post("/v1/vps/health")
async def vps_health():
    """Check VPS health status - useful for monitoring"""
    try:
        vps = get_vps_client()
        health = await vps.check_health()
        return health
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "available": False
        }
