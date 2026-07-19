from __future__ import annotations

import argparse
import importlib
import inspect
import sys
from typing import Any

from .application import SCICCLI
from .config import CLIConfig


def load_scic(specification: str) -> Any:
    """Load ``module:object`` and resolve a SCIC object or factory."""
    if ":" not in specification:
        raise ValueError("Application must use the form 'module:object'.")
    module_name, object_name = specification.split(":", 1)
    module = importlib.import_module(module_name)
    value = getattr(module, object_name)
    if callable(value) and not hasattr(value, "create_session"):
        value = value()
    if inspect.isawaitable(value):
        raise TypeError("Asynchronous SCIC factories are not supported by __main__.")
    if not hasattr(value, "create_session"):
        raise TypeError(f"{specification!r} did not resolve to a SCIC registry.")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m scic_cli",
        description="Launch an interactive shell for a SCIC registry.",
    )
    parser.add_argument("application", help="Import specification: module:object")
    parser.add_argument("--name", default="SCIC", help="Application display name")
    parser.add_argument("--no-banner", action="store_true")
    parser.add_argument("--no-history", action="store_true")
    parser.add_argument("--no-completion", action="store_true")
    parser.add_argument("--tracebacks", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        scic = load_scic(arguments.application)
        config = CLIConfig(
            application_name=arguments.name,
            show_banner=not arguments.no_banner,
            enable_history=not arguments.no_history,
            enable_completion=not arguments.no_completion,
            show_tracebacks=arguments.tracebacks,
        )
        return SCICCLI(scic, config=config).run()
    except Exception as error:
        print(f"scic-cli: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
