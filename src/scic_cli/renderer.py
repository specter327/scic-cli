from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from rich.console import Console
from rich import box
from rich.json import JSON
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from .errors import ErrorDiagnostic
from .schema import describe_contract


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
        table = self._table(title="Results")
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
        table = self._table()
        table.add_column("Type", width=12)
        table.add_column("Name")
        table.add_column("Description")
        for entry in entries:
            kind = entry.get("type", "unknown")
            marker = (
                Text("context", style="bold blue")
                if kind == "context"
                else Text("function", style="green")
            )
            table.add_row(
                marker,
                Text(str(entry.get("name", ""))),
                Text(str(entry.get("description") or "")),
            )
        self.console.print(table)

    def print_description(self, description: dict[str, Any]) -> None:
        title = f"{description.get('type', 'resource')}: {description.get('name', '')}"
        lines = []
        if description.get("description"):
            lines.append(str(description["description"]))
        if description.get("path"):
            lines.append(f"Path: {str(description['path']).lstrip('/')}")
        self.console.print(
            Panel(
                Text("\n".join(lines) or "No description."),
                title=Text(title),
            )
        )

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
        table = self._table(title="Shell commands")
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
        """Render a legacy, unstructured error."""
        message = str(error) or error.__class__.__name__
        self.console.print(f"[bold red]{error.__class__.__name__}:[/bold red] {message}")
        details = getattr(error, "details", None)
        if details:
            self.print_value(details)

    def print_diagnostic(self, diagnostic: ErrorDiagnostic) -> None:
        """Render an actionable explanation without exposing a traceback."""
        body = Text(diagnostic.message)

        if diagnostic.instruction:
            body.append("\nInstruction: ", style="bold")
            body.append(diagnostic.instruction, style="cyan")

        if diagnostic.code == "invalid_parameter":
            name = diagnostic.details.get("name")
            index = diagnostic.details.get("index")
            value = diagnostic.details.get("value")
            if name is not None:
                body.append("\nParameter: ", style="bold")
                body.append(str(name))
            if index is not None:
                body.append("\nPosition: ", style="bold")
                body.append(str(index))
            if value is not None:
                body.append("\nReceived: ", style="bold")
                body.append(str(value))

        self.console.print(
            Panel(
                body,
                title=diagnostic.title,
                border_style="red",
            )
        )

        if diagnostic.usage:
            self.console.print("[bold]Usage[/bold]")
            self.console.print(Text(f"  {diagnostic.usage}", style="cyan"))

        if diagnostic.executable is not None:
            self._print_contract(
                "Parameters",
                diagnostic.executable.get("parameters", []),
            )

        if diagnostic.suggestions:
            self.console.print("[bold]Did you mean?[/bold]")
            for suggestion in diagnostic.suggestions:
                self.console.print(Text(f"  {suggestion}", style="cyan"))

        if not diagnostic.expected:
            self.console.print(
                "[dim]This appears to be an application error. "
                "Run with --debug for the technical traceback.[/dim]"
            )

    def print_info(self, message: str) -> None:
        self.console.print(f"[cyan]{message}[/cyan]")

    def _print_contract(self, title: str, schemas: list[dict[str, Any]]) -> None:
        contract = describe_contract(
            schemas,
            item_label="parameter" if title == "Parameters" else "result",
        )
        table = self._table(title=title)
        table.add_column("#", justify="right")
        table.add_column("Name")
        table.add_column("Expected type")
        table.add_column("Description", ratio=2)
        table.add_column("Characteristics", ratio=2)
        if not contract:
            table.add_row("-", "-", "-", "None declared.", "-")
        for index, schema in enumerate(contract):
            table.add_row(
                str(index),
                Text(schema.name),
                Text(schema.data_type),
                Text(schema.description or "-"),
                Text("\n".join(schema.characteristics) or "-"),
            )
        self.console.print(table)

    @staticmethod
    def _table(*, title: str | None = None) -> Table:
        """Create a compact table without heavy header or outer borders."""
        return Table(
            title=title,
            box=box.SIMPLE_HEAD,
            show_edge=False,
            pad_edge=False,
            header_style="bold",
            collapse_padding=True,
        )

    def _build_tree(self, node: dict[str, Any]) -> Tree:
        kind = node.get("type", "resource")
        label = Text()
        label.append(
            "context" if kind == "context" else "function",
            style="bold blue" if kind == "context" else "green",
        )
        label.append(f" {node.get('name', '')}")
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
