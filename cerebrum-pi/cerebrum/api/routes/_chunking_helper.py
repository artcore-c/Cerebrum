# cerebrum/api/routes/_chunking_helper.py

"""Internal helper for chunking logic - keeps endpoints DRY"""
import logging
from cerebrum.retrieval import (
    chunk_text, should_chunk, select_top_chunks,
    dedupe_chunks, assemble_prompt, get_assembly_stats,
    extract_instruction, assemble_refactor_prompt
)

logger = logging.getLogger('CerebrumCM4')


def apply_smart_chunking(prompt: str) -> tuple[str, bool]:
    """
    Apply intelligent chunking if beneficial.
    
    Returns:
        (processed_prompt, was_chunked)
    """
    original_prompt = prompt
    
    # Extract instruction FIRST
    code, instruction = extract_instruction(prompt)
    
    if should_chunk(code):
        logger.info(f"Chunking large prompt: {len(code)} chars")
        
        chunks = chunk_text(code)
        unique_chunks = dedupe_chunks(chunks)
        logger.info(f"Deduplication: {len(chunks)} → {len(unique_chunks)} chunks")
        
        k = min(3, len(unique_chunks) - 1)
        
        if k <= 0:
            logger.info("Chunking skipped: insufficient unique chunks")
            return prompt, False
        
        query = instruction if instruction else code[-300:]
        selected_chunks = select_top_chunks(unique_chunks, query, k=k)
        
        if instruction:
            assembled_prompt = assemble_refactor_prompt(selected_chunks, instruction)
        else:
            # (explicit parameter names)
            assembled_prompt = assemble_prompt(
                user_prompt=code,
                chunks=selected_chunks
            )
        
        # Only use if meaningful reduction
        if len(assembled_prompt) >= len(original_prompt) * 0.9:
            logger.info(f"Chunking skipped: insufficient reduction")
            return prompt, False
        
        stats = get_assembly_stats(
            len(original_prompt),
            len(selected_chunks),
            len(assembled_prompt)
        )
        
        logger.info(
            f"Chunking complete: {stats['original_chars']} → {stats['final_chars']} chars "
            f"({stats['chunks_selected']} chunks, {stats['reduction_percent']}% reduction)"
        )
        
        return assembled_prompt, True
    
    elif instruction:
        # Has instruction but doesn't need chunking
        result = assemble_refactor_prompt([code], instruction)
        logger.info("Applied instruction-first prompt assembly")
        return result, False
    
    return prompt, False