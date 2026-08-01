from .application import SCICCLI
from .config import CLIConfig
from .errors import CLIError, CommandError, ErrorDiagnostic
from .renderer import ResultRenderer

__version__ = "0.2.0"

__all__ = [
    "SCICCLI",
    "CLIConfig",
    "CLIError",
    "CommandError",
    "ErrorDiagnostic",
    "ResultRenderer",
]
