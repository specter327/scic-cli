class CLIError(Exception):
    """Base error raised by scic-cli."""


class CommandError(CLIError):
    """Raised when a built-in shell command is invalid."""
