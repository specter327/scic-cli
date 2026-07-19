from __future__ import annotations

import shlex
from collections.abc import Iterable

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document

from .protocols import SCICSessionProtocol


_BUILTINS = (
    "help", "ls", "cd", "back", "root", "pwd", "describe", "tree",
    "clear", "exit", "quit",
)


class SCICCompleter(Completer):
    """Context-aware completer for SCIC resources and shell commands."""

    def __init__(self, session: SCICSessionProtocol) -> None:
        self._session = session

    def get_completions(self, document: Document, complete_event):
        text = document.text_before_cursor
        tokens, fragment = self._tokens(text)
        candidates = set(_BUILTINS)

        if tokens and tokens[0] in {"cd", "describe"}:
            candidates = self._children(only_contexts=tokens[0] == "cd")
        elif not tokens or len(tokens) <= 1:
            candidates.update(self._children())

        for candidate in sorted(candidates):
            if candidate.startswith(fragment):
                yield Completion(candidate, start_position=-len(fragment))

    def _children(self, only_contexts: bool = False) -> set[str]:
        result: set[str] = set()
        try:
            for entry in self._session.list_context():
                if only_contexts and entry.get("type") != "context":
                    continue
                name = entry.get("name")
                if name:
                    result.add(str(name))
        except Exception:
            return result
        return result

    @staticmethod
    def _tokens(text: str) -> tuple[list[str], str]:
        trailing_space = bool(text) and text[-1].isspace()
        try:
            parsed = shlex.split(text, posix=True)
        except ValueError:
            parsed = text.split()
        if trailing_space:
            return parsed, ""
        if not parsed:
            return [], text
        return parsed[:-1], parsed[-1]
