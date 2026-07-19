from __future__ import annotations

import asyncio
import os
import shlex
import traceback
from collections.abc import Callable
from typing import Any

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory, InMemoryHistory

from .completion import SCICCompleter
from .config import CLIConfig
from .errors import CommandError
from .protocols import SCICProtocol, SCICSessionProtocol
from .renderer import ResultRenderer


class SCICCLI:
    """Ready-to-use interactive shell for a local SCIC registry.

    One ``SCICCLI`` owns one independent ``SCICSession``. Multiple CLI clients
    can therefore share the same SCIC registry without sharing navigation state.
    """

    def __init__(
        self,
        scic: SCICProtocol,
        *,
        config: CLIConfig | None = None,
        renderer: ResultRenderer | None = None,
        session: SCICSessionProtocol | None = None,
    ) -> None:
        if not hasattr(scic, "create_session"):
            raise TypeError("scic must expose create_session().")
        self.scic = scic
        self.config = config or CLIConfig()
        self.renderer = renderer or ResultRenderer()
        self.session = session or scic.create_session()
        self._running = False
        self._prompt_session = self._create_prompt_session()

    def run(self) -> int:
        """Run the interactive shell from synchronous application code."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.run_async())
        raise RuntimeError(
            "SCICCLI.run() cannot be called inside a running event loop; "
            "use 'await cli.run_async()'."
        )

    async def run_async(self) -> int:
        """Run the interactive shell until the user exits."""
        self._running = True
        if self.config.show_banner:
            self.renderer.print_banner(self.config.application_name)

        while self._running:
            try:
                instruction = await self._prompt_session.prompt_async(
                    self._prompt_text()
                )
            except EOFError:
                break
            except KeyboardInterrupt:
                self.renderer.print_info("Use 'exit' or Ctrl-D to close the shell.")
                continue

            instruction = instruction.strip()
            if not instruction:
                continue

            try:
                await self.execute_line(instruction)
            except (KeyboardInterrupt, asyncio.CancelledError):
                self.renderer.print_info("Operation cancelled.")
            except Exception as error:
                self.renderer.print_error(error)
                if self.config.show_tracebacks:
                    self.renderer.console.print(traceback.format_exc())

        self._running = False
        return 0

    async def execute_line(self, instruction: str) -> list[Any] | None:
        """Execute one shell line, including built-ins and SCIC instructions."""
        tokens = self._split(instruction)
        if not tokens:
            return None

        command = tokens[0].lower()
        arguments = tokens[1:]
        handler = self._builtin_handlers().get(command)
        if handler is not None:
            result = handler(arguments)
            if asyncio.iscoroutine(result):
                await result
            return None

        results = await self.session.execute(instruction)
        self.renderer.print_results(results)
        return results

    async def execute(self, instruction: str) -> list[Any]:
        """Execute a raw SCIC instruction, bypassing shell built-ins."""
        results = await self.session.execute(instruction)
        self.renderer.print_results(results)
        return results

    def stop(self) -> None:
        self._running = False

    def _builtin_handlers(self) -> dict[str, Callable[[list[str]], Any]]:
        return {
            "help": self._cmd_help,
            "?": self._cmd_help,
            "ls": self._cmd_list,
            "cd": self._cmd_cd,
            "back": self._cmd_back,
            "..": self._cmd_back,
            "root": self._cmd_root,
            "/": self._cmd_root,
            "pwd": self._cmd_pwd,
            "describe": self._cmd_describe,
            "tree": self._cmd_tree,
            "clear": self._cmd_clear,
            "exit": self._cmd_exit,
            "quit": self._cmd_exit,
        }

    def _cmd_help(self, arguments: list[str]) -> None:
        self._require_count(arguments, 0, "help")
        self.renderer.print_help()

    def _cmd_list(self, arguments: list[str]) -> None:
        self._require_count(arguments, 0, "ls")
        self.renderer.print_context(self.session.list_context())

    def _cmd_cd(self, arguments: list[str]) -> None:
        self._require_count(arguments, 1, "cd <context>")
        self.session.enter(arguments[0])

    def _cmd_back(self, arguments: list[str]) -> None:
        self._require_count(arguments, 0, "back")
        self.session.back()

    def _cmd_root(self, arguments: list[str]) -> None:
        self._require_count(arguments, 0, "root")
        self.session.reset()

    def _cmd_pwd(self, arguments: list[str]) -> None:
        self._require_count(arguments, 0, "pwd")
        self.renderer.print_value(self.session.context_path)

    def _cmd_describe(self, arguments: list[str]) -> None:
        instruction = " ".join(arguments) if arguments else None
        self.renderer.print_description(self.session.describe(instruction))

    def _cmd_tree(self, arguments: list[str]) -> None:
        self._require_count(arguments, 0, "tree")
        self.renderer.print_tree(self.scic.export_tree())

    def _cmd_clear(self, arguments: list[str]) -> None:
        self._require_count(arguments, 0, "clear")
        os.system("cls" if os.name == "nt" else "clear")

    def _cmd_exit(self, arguments: list[str]) -> None:
        self._require_count(arguments, 0, "exit")
        self.stop()

    def _prompt_text(self) -> str:
        return f"{self.session.context_path} {self.config.prompt_symbol} "

    def _create_prompt_session(self) -> PromptSession:
        history = InMemoryHistory()
        if self.config.enable_history and self.config.history_file is not None:
            self.config.history_file.parent.mkdir(parents=True, exist_ok=True)
            history = FileHistory(str(self.config.history_file))

        completer = SCICCompleter(self.session) if self.config.enable_completion else None
        return PromptSession(history=history, completer=completer, complete_while_typing=False)

    @staticmethod
    def _split(instruction: str) -> list[str]:
        try:
            return shlex.split(instruction, posix=True)
        except ValueError as error:
            raise CommandError(f"Invalid shell syntax: {error}") from error

    @staticmethod
    def _require_count(arguments: list[str], expected: int, usage: str) -> None:
        if len(arguments) != expected:
            raise CommandError(f"Usage: {usage}")
