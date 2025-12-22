# cerebrum/retrieval/ranker.py

"""
Relevance Ranking for Chunks
============================

Lightweight lexical scoring - no embeddings required.
Fast enough for CM4, accurate enough for most cases.

File: /opt/cerebrum-pi/cerebrum/retrieval/ranker.py
"""

from typing import List


def score_chunk(chunk: str, query: str) -> int:
    """
    Score chunk relevance using keyword overlap.
    
    Args:
        chunk: Text chunk to score
        query: Query/prompt to match against
        
    Returns:
        Overlap score (higher = more relevant)
    """
    query_tokens = set(query.lower().split())
    chunk_tokens = set(chunk.lower().split())
    return len(query_tokens & chunk_tokens)


def dedupe_chunks(chunks: List[str]) -> List[str]:
    """
    Remove duplicate chunks using hash-based deduplication.
    
    Critical for repeated code patterns.
    
    Args:
        chunks: List of text chunks
        
    Returns:
        List of unique chunks
    """
    seen = set()
    unique = []
    
    for chunk in chunks:
        # Hash normalized chunk
        chunk_hash = hash(chunk.strip())
        
        if chunk_hash not in seen:
            seen.add(chunk_hash)
            unique.append(chunk)
    
    return unique


def select_top_chunks(
    chunks: List[str],
    query: str,
    k: int = 3
) -> List[str]:
    """
    Select top K most relevant chunks.
    
    Args:
        chunks: List of text chunks
        query: Query to match against
        k: Number of chunks to select
        
    Returns:
        List of top K chunks by relevance
    """
    if len(chunks) <= k:
        return chunks
    
    # Score and sort
    ranked = sorted(
        chunks,
        key=lambda c: score_chunk(c, query),
        reverse=True
    )
    
    return ranked[:k]