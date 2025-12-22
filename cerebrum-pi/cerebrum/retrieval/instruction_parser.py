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
    Extract instruction from prompt by scanning from end.
    
    Args:
        prompt: Full prompt text
        
    Returns:
        Tuple of (code, instruction)
        If no instruction found, returns (prompt, "")
    """
    lines = prompt.strip().splitlines()
    
    # Scan from end to find instruction markers
    MAX_SCAN_LINES = 12  # only scan last N lines

    for i in range(len(lines) - 1, max(len(lines) - MAX_SCAN_LINES, -1), -1):
        line = lines[i].strip()
        if any(line.startswith(m) for m in (
            "# INSTRUCTION:", "INSTRUCTION:", 
            "# REFACTOR:", "REFACTOR:",
            "# TODO:", "TODO:"
            )):
            code = "\n".join(lines[:i])
            instruction = "\n".join(lines[i:])
            return code.strip(), instruction.strip()
        
    return prompt, ""

def assemble_refactor_prompt(code_chunks: list, instruction: str) -> str:
    """
    Assemble prompt for code refactoring with instruction FIRST.
    
    Critical: Instruction must come first for base code models.
    
    Args:
        code_chunks: Selected code chunks
        instruction: Refactoring instruction
        
    Returns:
        Prompt with instruction prioritized
    """
    if not instruction:
        # No instruction, just join chunks
        return "\n\n".join(code_chunks)
    
    # Combine selected code
    combined_code = "\n\n".join(code_chunks)
    
    # Simple, direct format - instruction first, code second
    return f"""{instruction}

Here is the code to refactor:
```python
{combined_code}

Refactored code:
```python
"""