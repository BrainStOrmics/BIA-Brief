"""Task management tools for the ReAct agent."""

from __future__ import annotations

from langchain_core.tools import tool


def _format_tasks(tasks: list[dict]) -> str:
    """Format task list as a readable string."""
    lines = []
    for t in tasks:
        check = "x" if t["done"] else " "
        lines.append(f"  [{check}] Task {t['id']}: {t['desc']}")
    return "Task List:\n" + "\n".join(lines)


def create_task_tools() -> list:
    """Create task management tools with shared mutable state (closure).

    Returns:
        List of two tools: [create_task_list, mark_task_complete]
    """
    tasks: list[dict] = []

    @tool
    def create_task_list(task_descriptions: list[str]) -> str:
        """Create a numbered task list for the report generation workflow.

        Args:
            task_descriptions: List of task description strings.
        Returns:
            Formatted task list with IDs and status indicators.
        """
        tasks.clear()
        for i, desc in enumerate(task_descriptions):
            tasks.append({"id": i, "desc": desc, "done": False})
        return _format_tasks(tasks)

    @tool
    def mark_task_complete(task_id: int) -> str:
        """Mark a task as complete by its numeric ID.

        Args:
            task_id: The numeric ID of the task to mark complete.
        Returns:
            Updated task list showing current status.
        """
        for t in tasks:
            if t["id"] == task_id:
                t["done"] = True
                break
        return _format_tasks(tasks)

    @tool
    def list_tasks() -> str:
        """Return the current task list with completion status.

        Returns:
            Formatted task list showing which tasks are pending and complete.
        """
        if not tasks:
            return "Task List:\n  (no tasks created — call create_task_list first)"
        return _format_tasks(tasks)

    return [create_task_list, mark_task_complete, list_tasks]
