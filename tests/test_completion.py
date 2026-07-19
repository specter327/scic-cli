from prompt_toolkit.document import Document

from scic_cli.completion import SCICCompleter
from tests.fakes import FakeSession


def complete(text):
    completer = SCICCompleter(FakeSession())
    return [item.text for item in completer.get_completions(Document(text), None)]


def test_completes_resources():
    assert "math" in complete("ma")


def test_cd_only_completes_contexts():
    values = complete("cd ")
    assert "math" in values
    assert "status" not in values
