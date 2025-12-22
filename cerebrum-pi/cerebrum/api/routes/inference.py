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
from cerebrum.retrieval import (
    chunk_text,
    should_chunk,
    select_top_chunks,
    dedupe_chunks,  # NEW
    assemble_prompt,
    get_assembly_stats,
    extract_instruction,  # NEW
    assemble_refactor_prompt  # NEW
)

router = APIRouter(tags=["inference"])
logger = logging.getLogger('CerebrumCM4')

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
    vps = get_vps_client()
    
    # Apply chunking if needed
    original_prompt = request.prompt
    chunks_used = 0

    # Extract instruction if present (for refactoring tasks)
    code, instruction = extract_instruction(request.prompt)

    if should_chunk(code):  # Chunk only the code part
        logger.info(f"Chunking large prompt: {len(code)} chars")
    
        chunks = chunk_text(code)
    
        # Deduplicate chunks (huge win for repeated code)
        unique_chunks = dedupe_chunks(chunks)
        logger.info(f"Deduplication: {len(chunks)} → {len(unique_chunks)} chunks")
    
        # Cap k to ensure we actually reduce (leave at least 1 chunk out)
        k = min(3, len(unique_chunks) - 1)
    
        if k <= 0:
            # Too few chunks to be useful
            logger.info("Chunking skipped: insufficient unique chunks")
        else:
            # Rank against instruction if present, otherwise use end of code
            query = instruction if instruction else code[-300:]
            selected_chunks = select_top_chunks(unique_chunks, query, k=k)
        
            # Assemble based on whether we have an instruction
            if instruction:
                # Refactoring task - use structured prompt
                assembled_code = "\n\n".join(selected_chunks)
                assembled_prompt = assemble_refactor_prompt(assembled_code, instruction)
            else:
                # Regular task - use standard assembly
                assembled_prompt = assemble_prompt(code, selected_chunks)
        
            chunks_used = len(selected_chunks)
        
            # Only use chunked version if we actually reduced size meaningfully
            if len(assembled_prompt) >= len(original_prompt) * 0.9:
                logger.info(
                    f"Chunking skipped: insufficient reduction "
                    f"({len(assembled_prompt)} vs {len(original_prompt)} chars)"
                )
            else:
                stats = get_assembly_stats(
                    len(original_prompt),
                    chunks_used,
                    len(assembled_prompt)
                )
            
                logger.info(
                    f"Chunking complete: {stats['original_chars']} → {stats['final_chars']} chars "
                    f"({stats['chunks_selected']} chunks, {stats['reduction_percent']}% reduction)"
                )
            
                # Update request with assembled prompt
                request.prompt = assembled_prompt
    elif instruction:
        # Has instruction but doesn't need chunking
        # Still use structured prompt for better output
        request.prompt = assemble_refactor_prompt(code, instruction)
        logger.info("Applied instruction-aware prompt assembly")

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
    vps = get_vps_client()
    
    # Apply chunking if needed
    original_prompt = request.prompt
    chunks_used = 0

    # Extract instruction if present (for refactoring tasks)
    code, instruction = extract_instruction(request.prompt)

    if should_chunk(code):  # Chunk only the code part
        logger.info(f"Chunking large prompt: {len(code)} chars")
    
        chunks = chunk_text(code)
    
        # Deduplicate chunks (huge win for repeated code)
        unique_chunks = dedupe_chunks(chunks)
        logger.info(f"Deduplication: {len(chunks)} → {len(unique_chunks)} chunks")
    
        # Cap k to ensure we actually reduce (leave at least 1 chunk out)
        k = min(3, len(unique_chunks) - 1)
    
        if k <= 0:
            # Too few chunks to be useful
            logger.info("Chunking skipped: insufficient unique chunks")
        else:
            # Rank against instruction if present, otherwise use end of code
            query = instruction if instruction else code[-300:]
            selected_chunks = select_top_chunks(unique_chunks, query, k=k)
        
            # Assemble based on whether we have an instruction
            if instruction:
                # Refactoring task - use structured prompt
                assembled_code = "\n\n".join(selected_chunks)
                assembled_prompt = assemble_refactor_prompt(assembled_code, instruction)
            else:
                # Regular task - use standard assembly
                assembled_prompt = assemble_prompt(code, selected_chunks)
        
            chunks_used = len(selected_chunks)
        
            # Only use chunked version if we actually reduced size meaningfully
            if len(assembled_prompt) >= len(original_prompt) * 0.9:
                logger.info(
                    f"Chunking skipped: insufficient reduction "
                    f"({len(assembled_prompt)} vs {len(original_prompt)} chars)"
                )
            else:
                stats = get_assembly_stats(
                    len(original_prompt),
                    chunks_used,
                    len(assembled_prompt)
                )
            
                logger.info(
                    f"Chunking complete: {stats['original_chars']} → {stats['final_chars']} chars "
                    f"({stats['chunks_selected']} chunks, {stats['reduction_percent']}% reduction)"
                )
            
                # Update request with assembled prompt
                request.prompt = assembled_prompt
    elif instruction:
        # Has instruction but doesn't need chunking
        # Still use structured prompt for better output
        request.prompt = assemble_refactor_prompt(code, instruction)
        logger.info("Applied instruction-aware prompt assembly")

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