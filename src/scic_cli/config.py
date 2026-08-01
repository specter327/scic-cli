from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class CLIConfig:
    """Runtime configuration for :class:`SCICCLI`."""

    application_name: str = "SCIC"
    root_text: str | None = None
    root_color: str = "ansicyan"
    prompt_text: str = ">"
    prompt_color: str = "ansigreen"
    prompt_symbol: str | None = None
    history_file: Path | None = field(
        default_factory=lambda: Path.home() / ".scic_cli_history"
    )
    enable_history: bool = True
    enable_completion: bool = True
    enable_colors: bool = True
    show_banner: bool = True
    debug: bool = False
    show_tracebacks: bool | None = None
    confirm_exit: bool = False
    max_history_entries: int = 1_000

    def __post_init__(self) -> None:
        self.application_name = self.application_name.strip() or "SCIC"
        if self.root_text is not None:
            self.root_text = self.root_text.strip() or None
        self.root_color = self.root_color.strip()
        self.prompt_color = self.prompt_color.strip()

        # ``prompt_symbol`` was the public option in 0.1.0. Keep accepting it
        # while exposing the more precise ``prompt_text`` name.
        if self.prompt_symbol is not None:
            self.prompt_text = self.prompt_symbol
        self.prompt_text = self.prompt_text.strip() or ">"
        self.prompt_symbol = self.prompt_text

        # ``show_tracebacks`` is retained as a 0.1.x compatibility alias.
        # New integrations should use the clearer ``debug`` option.
        if self.show_tracebacks is not None:
            self.debug = self.show_tracebacks
        self.show_tracebacks = self.debug

        if self.max_history_entries < 1:
            raise ValueError("max_history_entries must be greater than zero.")
        if self.history_file is not None and not isinstance(self.history_file, Path):
            self.history_file = Path(self.history_file)
