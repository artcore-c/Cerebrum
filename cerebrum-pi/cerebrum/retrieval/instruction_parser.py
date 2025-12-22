# cerebrum/retrieval/instruction_parser.py

"""
Instruction Parsing for Code Tasks
==================================

Separates instructions from code for better model behavior.

File: /opt/cerebrum-pi/cerebrum/retrieval/instruction_parser.py
"""

from typing import Tuple


def extract_instruction(prompt: str) -> Tuple[str, str]:
    """
    Extract instruction from prompt if present.
    
    Args:
        prompt: Full prompt text
        
    Returns:
        Tuple of (code, instruction)
        If no instruction found, returns (prompt, "")
    """
    markers = [
        "# INSTRUCTION:",
        "# TODO:",
        "INSTRUCTION:",
        "TODO:",
        "# Task:",
        "Task:"
    ]
    
    for marker in markers:
        if marker in prompt:
            # Split on LAST occurrence (instruction usually at end)
            parts = prompt.rsplit(marker, 1)
            if len(parts) == 2:
                code = parts[0].strip()
                instruction = marker + parts[1].strip()
                return code, instruction
    
    return prompt, ""


def assemble_refactor_prompt(code: str, instruction: str) -> str:
    """
    Assemble prompt for code refactoring tasks.
    
    Forces model to output code, not explanations.
    
    Args:
        code: Source code to refactor
        instruction: Refactoring instruction
        
    Returns:
        Structured prompt
    """
    if not instruction:
        return code
    
    return f"""SYSTEM:
You are an expert Python engineer.
You must refactor the provided code exactly as instructed.
Return ONLY valid Python code. No explanations. No comments about what you're doing.

USER INSTRUCTION:
{instruction}

CODE:
{code}

REFACTORED CODE:"""