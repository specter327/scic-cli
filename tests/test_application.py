import pytest

from scic_cli import CLIConfig, SCICCLI
from tests.fakes import FakeSCIC


class SilentRenderer:
    def __init__(self):
        self.results = []
        self.values = []

    def print_results(self, results): self.results.append(results)
    def print_value(self, value): self.values.append(value)
    def print_banner(self, *args): pass
    def print_help(self): pass
    def print_context(self, *args): pass
    def print_description(self, *args): pass
    def print_tree(self, *args): pass
    def print_info(self, *args): pass
    def print_error(self, *args): pass


@pytest.mark.asyncio
async def test_executes_scic_instruction(tmp_path):
    scic = FakeSCIC()
    renderer = SilentRenderer()
    cli = SCICCLI(
        scic,
        renderer=renderer,
        config=CLIConfig(history_file=tmp_path / "history", enable_history=False),
    )

    result = await cli.execute_line("math add 20 22")

    assert result == [42]
    assert scic.session.executed == ["math add 20 22"]
    assert renderer.results == [[42]]


@pytest.mark.asyncio
async def test_navigation_builtins(tmp_path):
    scic = FakeSCIC()
    cli = SCICCLI(
        scic,
        renderer=SilentRenderer(),
        config=CLIConfig(history_file=tmp_path / "history", enable_history=False),
    )

    await cli.execute_line("cd math")
    assert cli.session.context_path == "scic/math"
    await cli.execute_line("back")
    assert cli.session.context_path == "scic"
