# cerebrum/retrieval/__init__.py
"""Retrieval and chunking utilities"""

from .chunker import chunk_text, should_chunk
from .ranker import score_chunk, select_top_chunks, dedupe_chunks
from .assembler import assemble_prompt, get_assembly_stats
from .instruction_parser import extract_instruction, assemble_refactor_prompt

__all__ = [
    "chunk_text",
    "should_chunk",
    "score_chunk",
    "select_top_chunks",
    "dedupe_chunks",
    "assemble_prompt",
    "get_assembly_stats",
    "extract_instruction",
    "assemble_refactor_prompt"
]