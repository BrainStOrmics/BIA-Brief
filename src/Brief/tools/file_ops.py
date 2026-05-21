"""File operation tools for the ReAct agent."""

from __future__ import annotations

import os

from langchain_core.tools import tool


@tool
def read_file(path: str) -> str:
    """Read a file and return its contents as a string.

    Args:
        path: Absolute or relative path to the file to read.
    Returns:
        The file contents as a string.
    Raises:
        FileNotFoundError: If the file does not exist.
    """
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@tool
def write_file(path: str, content: str) -> str:
    """Write content to a file. Creates parent directories if needed.

    Args:
        path: Absolute or relative path to the output file.
        content: The string content to write.
    Returns:
        Confirmation message with character count and path.
    """
    abs_path = os.path.abspath(path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Written {len(content)} chars to {abs_path}"
