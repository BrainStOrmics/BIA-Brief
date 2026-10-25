"""Human review prompts, timeout handling, and resume feedback."""

from __future__ import annotations

import logging
import os
import sys
import time
from typing import Callable, TextIO

logger = logging.getLogger(__name__)

APPROVAL_FEEDBACK = ""


def _env_auto_approves() -> bool:
    return os.environ.get("BRIEF_AUTO_APPROVE") == "1"


class ReviewGate:
    """Own the interface between Graph interrupts and human review."""

    def __init__(
        self,
        *,
        auto_approve: bool | None = None,
        timeout: int = 300,
        input_stream: TextIO | None = None,
        output_stream: TextIO | None = None,
        line_reader: Callable[[int], str] | None = None,
    ) -> None:
        self.auto_approve = _env_auto_approves() if auto_approve is None else auto_approve
        self.timeout = max(0, int(timeout))
        self.input_stream = input_stream or sys.stdin
        self.output_stream = output_stream or sys.stdout
        self._line_reader = line_reader

    def review(self, message: str) -> str:
        """Return reviewer feedback, or an empty string for approval."""
        if self.auto_approve:
            logger.info("HITL auto-approved: %s", message[:120])
            return APPROVAL_FEEDBACK

        print("\n" + "=" * 60, file=self.output_stream)
        print(message, file=self.output_stream)
        timeout_text = f"{self.timeout}s 超时" if self.timeout else "无超时"
        print(f"编辑后按 Enter 继续（{timeout_text}）", file=self.output_stream)
        print("=" * 60, file=self.output_stream)
        return self._read_feedback()

    def _read_feedback(self) -> str:
        if self._line_reader is not None:
            return self._line_reader(self.timeout).strip()
        if sys.platform == "win32" and self._is_console():
            return _read_windows_console_line(self.input_stream, self.output_stream, self.timeout)
        return _read_stream_line(self.input_stream, self.timeout)

    def _is_console(self) -> bool:
        isatty = getattr(self.input_stream, "isatty", None)
        return bool(isatty and isatty())


def _read_stream_line(stream: TextIO, timeout: int) -> str:
    """Read one line from a stream, using select for POSIX timeouts."""
    if timeout:
        import select

        try:
            ready, _, _ = select.select([stream], [], [], timeout)
        except (OSError, ValueError):
            ready = [stream]
        if not ready:
            logger.warning("Human review timed out after %ss", timeout)
            return APPROVAL_FEEDBACK

    try:
        return stream.readline().rstrip("\r\n")
    except EOFError:
        return APPROVAL_FEEDBACK


def _read_windows_console_line(stream: TextIO, output_stream: TextIO, timeout: int) -> str:
    """Read a console line on Windows without blocking past the timeout."""
    import msvcrt

    chars: list[str] = []
    deadline = time.monotonic() + timeout if timeout else None
    while True:
        if msvcrt.kbhit():
            char = msvcrt.getwch()
            if char in ("\r", "\n"):
                output_stream.write("\n")
                output_stream.flush()
                return "".join(chars)
            if char == "\x03":
                raise KeyboardInterrupt
            if char in ("\x08", "\x7f"):
                if chars:
                    chars.pop()
                    output_stream.write("\b \b")
                    output_stream.flush()
                continue
            if char in ("\x00", "\xe0"):
                if msvcrt.kbhit():
                    msvcrt.getwch()
                continue
            chars.append(char)
            output_stream.write(char)
            output_stream.flush()
            continue

        if deadline is not None and time.monotonic() >= deadline:
            output_stream.write("\n")
            output_stream.flush()
            logger.warning("Human review timed out after %ss", timeout)
            return APPROVAL_FEEDBACK
        time.sleep(0.03)
