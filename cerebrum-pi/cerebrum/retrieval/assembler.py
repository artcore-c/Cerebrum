# cerebrum/retrieval/assembler.py

"""
Prompt Assembly for RAG
=======================

Combines user prompt with retrieved context chunks
in a format optimized for code generation models.

File: /opt/cerebrum-pi/cerebrum/retrieval/assembler.py
"""

from typing import List, Optional


def assemble_prompt(
    user_prompt: str,
    chunks: Optional[List[str]] = None,
    max_context_chars: int = 2500
) -> str:
    """
    Assemble final prompt with context chunks.
    
    Args:
        user_prompt: Original user prompt
        chunks: Optional list of context chunks
        max_context_chars: Maximum total context size
        
    Returns:
        Assembled prompt ready for inference
    """
    if not chunks:
        return user_prompt
    
    # Build context blocks
    context_blocks = []
    total_chars = len(user_prompt)
    
    for i, chunk in enumerate(chunks):
        if total_chars + len(chunk) > max_context_chars:
            break
        
        context_blocks.append(f"CONTEXT {i+1}:\n{chunk}")
        total_chars += len(chunk)
    
    if not context_blocks:
        return user_prompt
    
    context_str = "\n\n".join(context_blocks)
    
    return f"""SYSTEM:
You are an expert code assistant. Use the context below only if relevant.

{context_str}

USER:
{user_prompt}
"""


def get_assembly_stats(
    original_length: int,
    chunks_selected: int,
    final_length: int
) -> dict:
    """
    Get statistics about prompt assembly.
    
    Returns:
        Dictionary with assembly statistics
    """
    return {
        "original_chars": original_length,
        "chunks_selected": chunks_selected,
        "final_chars": final_length,
        "reduction_percent": round(
            (1 - final_length / original_length) * 100, 1
        ) if original_length > 0 else 0
    }