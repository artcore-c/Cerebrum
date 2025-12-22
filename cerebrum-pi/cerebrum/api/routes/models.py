# cerebrum/api/routes/models.py

"""Model listing routes"""
from fastapi import APIRouter
from cerebrum.core.vps_client import get_vps_client

router = APIRouter(tags=["models"])

@router.get("/v1/models")
async def list_models():
    """List available models from VPS backend"""
    try:
        vps = get_vps_client()
        vps_models = await vps.list_models()
        # Explicit transformation
        return {
            "available_models": vps_models.get("available_models", []),
            "cached_models": vps_models.get("cached_models", []),
            "inference_counts": vps_models.get("inference_counts", {})
        }
    except Exception as e:
        return {
            "error": str(e),
            "vps_models": []
        }
