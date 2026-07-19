# scic-cli

A ready-to-use interactive shell client for applications built with
[`scic-framework`](https://github.com/specter327/scic-framework).

`scic-cli` does not implement application business logic. It creates an
independent `SCICSession`, presents the registered context tree, resolves user
instructions, executes functions, and renders structured results.

## Features

- Interactive shell based on `prompt-toolkit`.
- One independent SCIC navigation session per client.
- Context-aware resource completion.
- Persistent command history.
- Rich tables, JSON, errors, descriptions, and tree rendering.
- Native support for synchronous and asynchronous SCIC functions.
- Built-in navigation and inspection commands.
- Works on Linux, Windows, and macOS.
- Programmatic API and `python -m scic_cli` launcher.

## Installation

```bash
python -m pip install scic-cli
```

For development:

```bash
python -m pip install -e ".[test,build]"
pytest
```

## Application integration

```python
from scic_cli import CLIConfig, SCICCLI

cli = SCICCLI(
    scic,
    config=CLIConfig(application_name="OpenShell Manager"),
)

raise SystemExit(cli.run())
```

Inside an existing event loop:

```python
await cli.run_async()
```

Each `SCICCLI` creates its own `SCICSession`, so several CLI, WebGUI, API, or
DesktopGUI clients can share the same frozen SCIC registry without sharing
navigation state.

## Generic launcher

Expose a SCIC object or zero-argument factory from a Python module:

```python
# my_application.py
application = build_scic_application()
```

Launch it without writing a dedicated CLI entrypoint:

```bash
python -m scic_cli my_application:application --name "My Application"
```

A factory is also valid:

```bash
python -m scic_cli my_application:build_application
```

## Shell commands

| Command | Purpose |
|---|---|
| `help`, `?` | Show help |
| `ls` | List the active context |
| `cd <context>` | Enter a child context |
| `back`, `..` | Move to the parent context |
| `root`, `/` | Return to the root context |
| `pwd` | Print the active context path |
| `describe [path]` | Describe a context or executable |
| `tree` | Render the complete registry tree |
| `clear` | Clear the terminal |
| `exit`, `quit` | Close the shell |

Any other line is forwarded unchanged to `SCICSession.execute()`.

Example:

```text
scic > ls
scic > cd math
scic/math > add 20 22
42
scic/math > describe add
scic/math > back
scic > exit
```

SCIC quoting uses the framework parser. Complex values can be passed as JSON
strings where the registered `Executable` supports them.

## Design boundaries

`scic-cli` owns presentation and interactive navigation. It does not own:

- SCIC registry construction;
- business functions;
- permissions or authentication;
- remote transport;
- HTTP APIs;
- application persistence.

Those concerns remain in the application or in other SCIC clients.

## Publishing

Run checks and build distributions:

```bash
./check.sh
```

Publish to TestPyPI:

```bash
./publish.sh --test
```

Publish to PyPI:

```bash
./publish.sh
```

The included GitHub Actions workflow can publish releases using PyPI Trusted
Publishing after the repository/environment is configured.

## License

MIT.
