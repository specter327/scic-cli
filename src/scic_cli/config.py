from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class CLIConfig:
    """Runtime configuration for :class:`SCICCLI`."""

    application_name: str = "SCIC"
    prompt_symbol: str = ">"
    history_file: Path | None = field(
        default_factory=lambda: Path.home() / ".scic_cli_history"
    )
    enable_history: bool = True
    enable_completion: bool = True
    enable_colors: bool = True
    show_banner: bool = True
    show_tracebacks: bool = False
    confirm_exit: bool = False
    max_history_entries: int = 1_000

    def __post_init__(self) -> None:
        self.application_name = self.application_name.strip() or "SCIC"
        self.prompt_symbol = self.prompt_symbol.strip() or ">"
        if self.max_history_entries < 1:
            raise ValueError("max_history_entries must be greater than zero.")
        if self.history_file is not None and not isinstance(self.history_file, Path):
            self.history_file = Path(self.history_file)
