from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


class CLIError(Exception):
    """Base error raised by scic-cli."""


class CommandError(CLIError):
    """Raised when a built-in shell command is invalid."""

    def __init__(self, message: str, *, usage: str | None = None) -> None:
        self.message = message
        self.usage = usage
        self.details = {"usage": usage} if usage else {}
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class ErrorDiagnostic:
    """Structured, presentation-independent explanation of a CLI failure."""

    title: str
    message: str
    code: str
    instruction: str | None = None
    details: Mapping[str, Any] = field(default_factory=dict)
    usage: str | None = None
    executable: Mapping[str, Any] | None = None
    suggestions: tuple[str, ...] = ()
    expected: bool = True
