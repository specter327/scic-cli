from __future__ import annotations

import shlex

from difflib import get_close_matches
from typing import Any, Mapping

from .errors import CLIError, ErrorDiagnostic
from .schema import describe_contract


_TITLES = {
    "command_error": "Invalid command",
    "invalid_instruction": "Invalid instruction",
    "resource_not_found": "Resource not found",
    "context_expected": "Context expected",
    "executable_expected": "Function expected",
    "invalid_parameters": "Invalid parameters",
    "invalid_parameter": "Invalid parameter",
    "invalid_results": "Application contract error",
    "invalid_result": "Application contract error",
    "executable_not_bound": "Application contract error",
}

_EXPECTED_CODES = {
    "command_error",
    "invalid_instruction",
    "resource_not_found",
    "context_expected",
    "executable_expected",
    "invalid_parameters",
    "invalid_parameter",
}


def build_diagnostic(
    error: BaseException,
    *,
    instruction: str | None,
    session: Any,
    tree: Mapping[str, Any] | None = None,
) -> ErrorDiagnostic:
    """Turn CLI/SCIC exceptions into actionable terminal diagnostics."""

    code = _error_code(error)
    details = _error_details(error)
    message = str(error) or error.__class__.__name__
    executable = None
    target_tokens: tuple[str, ...] = ()

    if instruction and code in {"invalid_parameters", "invalid_parameter"}:
        executable, target_tokens = _find_executable(session, instruction)

    usage = getattr(error, "usage", None)
    if executable is not None:
        usage = _build_usage(target_tokens, executable)

    if code == "invalid_parameters":
        expected = details.get("expected")
        received = details.get("received")
        if expected is not None and received is not None:
            message = (
                "Incorrect parameter count. "
                f"Expected {expected}, received {received}."
            )

    suggestions = _suggestions(
        error,
        instruction=instruction,
        tree=tree,
    )

    return ErrorDiagnostic(
        title=_TITLES.get(code, "Unexpected error"),
        message=message,
        code=code,
        instruction=instruction,
        details=details,
        usage=usage,
        executable=executable,
        suggestions=suggestions,
        expected=isinstance(error, CLIError) or code in _EXPECTED_CODES,
    )


def _error_code(error: BaseException) -> str:
    code = getattr(error, "code", None)
    if code:
        return str(code)
    if isinstance(error, CLIError):
        return "command_error"
    return "unexpected_error"


def _error_details(error: BaseException) -> dict[str, Any]:
    details = getattr(error, "details", None)
    if isinstance(details, Mapping):
        return dict(details)
    return {}


def _find_executable(
    session: Any,
    instruction: str,
) -> tuple[Mapping[str, Any] | None, tuple[str, ...]]:
    try:
        tokens = tuple(shlex.split(instruction, posix=True))
    except ValueError:
        return None, ()

    for end in range(len(tokens), 0, -1):
        candidate_tokens = tokens[:end]
        candidate = shlex.join(candidate_tokens)

        try:
            description = session.describe(candidate)
        except Exception:
            continue

        if (
            isinstance(description, Mapping)
            and description.get("type") == "executable"
        ):
            return description, candidate_tokens

    return None, ()


def _build_usage(
    target_tokens: tuple[str, ...],
    executable: Mapping[str, Any],
) -> str:
    parameters = describe_contract(
        executable.get("parameters", []),
        item_label="parameter",
    )
    parts = [*target_tokens]
    parts.extend(
        f"<{parameter.name}:{parameter.data_type}>"
        for parameter in parameters
    )
    return " ".join(parts)


def _suggestions(
    error: BaseException,
    *,
    instruction: str | None,
    tree: Mapping[str, Any] | None,
) -> tuple[str, ...]:
    if not instruction:
        return ()

    try:
        tokens = shlex.split(instruction, posix=True)
    except ValueError:
        return ()

    # Built-ins belong to the CLI and must lead the line. This catches the
    # especially confusing "domains describe list" form.
    for index, token in enumerate(tokens[1:], start=1):
        if token.lower() == "describe":
            corrected = ["describe", *tokens[:index], *tokens[index + 1 :]]
            return (shlex.join(corrected),)

    if getattr(error, "code", None) != "resource_not_found":
        return ()

    missing = str(getattr(error, "token", "") or "")
    context_path = str(getattr(error, "context_path", "") or "")
    candidates = _context_children(tree, context_path)
    matches = get_close_matches(missing, candidates, n=3, cutoff=0.55)
    suggestions: list[str] = []

    for match in matches:
        corrected = list(tokens)
        try:
            index = corrected.index(missing)
        except ValueError:
            continue
        corrected[index] = match
        suggestions.append(shlex.join(corrected))

    return tuple(suggestions)


def _context_children(
    tree: Mapping[str, Any] | None,
    context_path: str,
) -> list[str]:
    if not isinstance(tree, Mapping):
        return []

    normalized_path = "/" + context_path.strip("/")

    def visit(node: Mapping[str, Any]) -> Mapping[str, Any] | None:
        node_path = "/" + str(node.get("path", "")).strip("/")
        if node_path == normalized_path:
            return node
        for child in node.get("children", []) or []:
            if isinstance(child, Mapping):
                found = visit(child)
                if found is not None:
                    return found
        return None

    context = visit(tree)
    if context is None:
        return []
    return [
        str(child.get("name"))
        for child in context.get("children", []) or []
        if isinstance(child, Mapping) and child.get("name")
    ]
