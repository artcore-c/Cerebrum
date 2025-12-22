# cerebrum/api/routes/inference.py

"""Inference routes"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from datetime import datetime
import json
import time
import logging
from cerebrum.core.vps_client import (
    get_vps_client,
    VPSUnavailableError,
    VPSInferenceError
)

from ._chunking_helper import apply_smart_chunking  

router = APIRouter(tags=["inference"])
logger = logging.getLogger('CerebrumCM4')

# Model mapping for language-specific routing
_MODEL_MAP = {
    "python": "qwen_7b",
    "javascript": "qwen_7b",
    "typescript": "qwen_7b",
    "rust": "codellama_7b",
    "go": "codellama_7b",
    "c": "codellama_7b",
    "cpp": "codellama_7b",
}

_DEFAULT_MODEL = "qwen_7b"  # Fallback for unknown languages

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

@router.post("/v1/complete", response_model=CodeCompletionResponse)
async def code_completion(request: CodeCompletionRequest):
    """Code completion endpoint - routes to VPS for inference"""
    
    # Protect CM4 memory + VPS bandwidth from oversized prompts
    if len(request.prompt) > 16_000:
        raise HTTPException(413, "Prompt exceeds 16KB limit")
    
    logger.info(f"Code completion request: {request.language} ({len(request.prompt)} chars)")
    
    start_time = time.time()
    
    # Determine model based on language
    model = _MODEL_MAP.get(request.language.lower(), _DEFAULT_MODEL)
    vps = get_vps_client()

    # Apply smart chunking (all logic in helper)
    request.prompt, was_chunked = apply_smart_chunking(request.prompt)

    # Try VPS inference
    try:
        result = await vps.inference(
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

@router.post("/v1/complete/stream")
async def stream_completion(request: CodeCompletionRequest):
    """
    Streaming code completion endpoint.
    
    Returns Server-Sent Events with tokens as they're generated.
    """
    logger.info(f"Streaming request: {request.language} ({len(request.prompt)} chars)")
    
    # Protect against oversized prompts
    if len(request.prompt) > 16_000:
        raise HTTPException(413, "Prompt exceeds 16KB limit")

    # Determine model
    model = _MODEL_MAP.get(request.language.lower(), _DEFAULT_MODEL)
    vps = get_vps_client()

    # Apply smart chunking (same logic)
    request.prompt, was_chunked = apply_smart_chunking(request.prompt)

    async def generate():
        try:
            start_time = time.time()
            tokens_received = 0
            
            async for chunk in vps.inference_stream(
                prompt=request.prompt,
                model=model,
                max_tokens=request.max_tokens,
                temperature=request.temperature
            ):
                # Forward tokens to client
                if "token" in chunk:
                    tokens_received += 1
                    yield f"data: {json.dumps(chunk)}\n\n"
                
                # Forward completion event
                elif chunk.get("done"):
                    inference_time = time.time() - start_time
                    completion = {
                        "done": True,
                        "language": request.language,
                        "model": model,
                        "total_tokens": tokens_received,
                        "inference_time": round(inference_time, 3),
                        "timestamp": datetime.now().isoformat()
                    }
                    yield f"data: {json.dumps(completion)}\n\n"
                    
                    logger.info(
                        f"Stream complete: {tokens_received} tokens in {inference_time:.2f}s"
                    )
        
        except VPSUnavailableError as e:
            error = {"error": "VPS unavailable", "message": str(e), "done": True}
            yield f"data: {json.dumps(error)}\n\n"
        
        except Exception as e:
            error = {"error": "Streaming failed", "message": str(e), "done": True}
            yield f"data: {json.dumps(error)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )