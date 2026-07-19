from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.json import JSON
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree


class ResultRenderer:
    """Renders SCIC metadata, results, and errors for a terminal."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def print_banner(self, application_name: str) -> None:
        self.console.print(
            Panel.fit(
                f"[bold]{application_name}[/bold]\n"
                "Interactive SCIC command shell. Type [bold]help[/bold] for commands.",
                border_style="cyan",
            )
        )

    def print_results(self, results: list[Any]) -> None:
        if not results:
            return
        if len(results) == 1:
            self.print_value(results[0])
            return
        table = Table(title="Results", show_lines=True)
        table.add_column("#", justify="right")
        table.add_column("Value")
        for index, value in enumerate(results):
            table.add_row(str(index), self._renderable_text(value))
        self.console.print(table)

    def print_value(self, value: Any) -> None:
        normalized = self._normalize(value)
        if isinstance(normalized, (dict, list)):
            self.console.print(JSON.from_data(normalized, indent=2, sort_keys=True))
        elif normalized is None:
            self.console.print("[dim]None[/dim]")
        else:
            self.console.print(normalized)

    def print_context(self, entries: tuple[dict[str, Any], ...]) -> None:
        if not entries:
            self.console.print("[dim]Context is empty.[/dim]")
            return
        table = Table(show_header=True, header_style="bold")
        table.add_column("Type", width=12)
        table.add_column("Name")
        table.add_column("Description")
        for entry in entries:
            kind = entry.get("type", "unknown")
            marker = "context" if kind == "context" else "function"
            table.add_row(marker, str(entry.get("name", "")), str(entry.get("description") or ""))
        self.console.print(table)

    def print_description(self, description: dict[str, Any]) -> None:
        title = f"{description.get('type', 'resource')}: {description.get('name', '')}"
        lines = []
        if description.get("description"):
            lines.append(str(description["description"]))
        if description.get("path"):
            lines.append(f"Path: {str(description['path']).lstrip('/')}")
        self.console.print(Panel("\n".join(lines) or "No description.", title=title))

        if description.get("type") == "executable":
            self._print_contract("Parameters", description.get("parameters", []))
            self._print_contract("Results", description.get("results", []))
        elif "children" in description:
            self.print_context(tuple(description.get("children", [])))

        metadata = description.get("metadata") or {}
        if metadata:
            self.console.print("[bold]Metadata[/bold]")
            self.print_value(metadata)

    def print_tree(self, description: dict[str, Any]) -> None:
        root = self._build_tree(description)
        self.console.print(root)

    def print_help(self) -> None:
        table = Table(title="Shell commands", show_lines=False)
        table.add_column("Command", style="bold")
        table.add_column("Description")
        commands = (
            ("help, ?", "Show this help."),
            ("ls", "List contexts and functions in the current context."),
            ("cd <context>", "Enter a context."),
            ("back, ..", "Move to the parent context."),
            ("root, /", "Return to the root context."),
            ("pwd", "Print the active SCIC context path."),
            ("describe [path]", "Describe the current or selected resource."),
            ("tree", "Render the complete SCIC resource tree."),
            ("clear", "Clear the terminal."),
            ("exit, quit", "Close the shell."),
            ("<instruction>", "Execute a SCIC context/function instruction."),
        )
        for command, description in commands:
            table.add_row(command, description)
        self.console.print(table)

    def print_error(self, error: BaseException) -> None:
        message = str(error) or error.__class__.__name__
        self.console.print(f"[bold red]{error.__class__.__name__}:[/bold red] {message}")
        details = getattr(error, "details", None)
        if details:
            self.print_value(details)

    def print_info(self, message: str) -> None:
        self.console.print(f"[cyan]{message}[/cyan]")

    def _print_contract(self, title: str, schemas: list[dict[str, Any]]) -> None:
        table = Table(title=title)
        table.add_column("#", justify="right")
        table.add_column("Name")
        table.add_column("Type")
        table.add_column("Constraints")
        if not schemas:
            table.add_row("-", "-", "-", "None")
        for index, schema in enumerate(schemas):
            data_type = schema.get("data_type") or schema.get("type") or "unknown"
            name = schema.get("name") or f"value_{index}"
            constraints = {
                key: value
                for key, value in schema.items()
                if key not in {"name", "data_type", "type", "value"}
                and value not in (None, [], {}, ())
            }
            table.add_row(str(index), str(name), str(data_type), self._renderable_text(constraints))
        self.console.print(table)

    def _build_tree(self, node: dict[str, Any]) -> Tree:
        kind = node.get("type", "resource")
        icon = "[bold blue]context[/bold blue]" if kind == "context" else "[green]function[/green]"
        label = f"{icon} {node.get('name', '')}"
        tree = Tree(label)
        for child in node.get("children", []) or []:
            tree.add(self._build_tree(child))
        return tree

    def _renderable_text(self, value: Any) -> str:
        normalized = self._normalize(value)
        if isinstance(normalized, (dict, list)):
            return json.dumps(normalized, ensure_ascii=False, default=str)
        return str(normalized)

    @classmethod
    def _normalize(cls, value: Any) -> Any:
        if is_dataclass(value):
            return cls._normalize(asdict(value))
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, dict):
            return {str(key): cls._normalize(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set, frozenset)):
            return [cls._normalize(item) for item in value]
        if hasattr(value, "to_dict") and callable(value.to_dict):
            try:
                return cls._normalize(value.to_dict())
            except Exception:
                pass
        return value
