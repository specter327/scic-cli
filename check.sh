#!/usr/bin/env bash
set -euo pipefail
python3 -m pip install -e '.[test,build]' --break-system-packages;
python3 -m pytest
python3 -m build
python3 -m twine check dist/*
