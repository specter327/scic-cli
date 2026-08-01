#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

git add .;
git commit -m "New update";
git push origin main;

python3 -m pip install --upgrade build twine --break-system-packages
rm -rf build dist ./*.egg-info src/*.egg-info
python3 -m build
python3 -m twine check dist/*

if [[ "${1:-}" == "--test" ]]; then
    python3 -m twine upload --repository testpypi dist/* --verbose
else
    python3 -m twine upload dist/* --verbose
fi
