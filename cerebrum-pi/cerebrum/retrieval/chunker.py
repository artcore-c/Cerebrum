# cerebrum/retrieval/chunker.py

"""
Text Chunking for Large Inputs
==============================

Splits large text into manageable chunks with overlap
to preserve context boundaries.

File: /opt/cerebrum-pi/cerebrum/retrieval/chunker.py
"""

from typing import List


def chunk_text(
    text: str,
    max_chars: int = 1000,
    overlap: int = 150
) -> List[str]:
    """
    Split text into overlapping chunks.
    
    Args:
        text: Input text to chunk
        max_chars: Maximum characters per chunk
        overlap: Characters to overlap between chunks
        
    Returns:
        List of text chunks
    """
    if len(text) <= max_chars:
        return [text]
    
    chunks = []
    start = 0
    length = len(text)
    
    while start < length:
        end = min(start + max_chars, length)
        chunks.append(text[start:end])
        start = end - overlap
    
    return chunks


def should_chunk(text: str, threshold: int = 1500) -> bool:
    """
    Determine if text should be chunked.
    
    Args:
        text: Input text
        threshold: Character threshold for chunking
        
    Returns:
        True if text should be chunked
    """
    return len(text) > threshold