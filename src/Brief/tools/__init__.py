"""Tools for the ReAct agent."""

from .file_ops import read_file, write_file
from .task_ops import create_task_tools


def create_tools() -> list:
    """Create the full tools list for the ReAct agent.

    Returns:
        List of all tools: [read_file, write_file, create_task_list, mark_task_complete]
    """
    task_tools = create_task_tools()
    return [read_file, write_file] + task_tools
