#!/usr/bin/env bash
# Recreate .venv with a real CPython (not the Cursor AppImage, not a tiny /usr/bin shim).
# If `python -m venv` was ever run while `python3` launched Cursor, pyvenv.cfg will
# point at the AppImage and `python -m pytest` will fail with "No module named pytest"
# (because pytest was installed in a venv that is never actually CPython).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

candidates=()
if [[ -n "${PYTHON_BOOTSTRAP:-}" ]]; then
  candidates+=("${PYTHON_BOOTSTRAP}")
fi
# Prefer a full install (e.g. python.org / /usr/local); Fedora's /usr/bin/python3.12
# is often a ~16kB wrapper — still try, but the size check may skip it.
for c in /usr/local/bin/python3.12 /usr/local/bin/python3.11 /usr/bin/python3.12 /usr/bin/python3.11 /usr/bin/python3; do
  if [[ -x "$c" ]]; then
    candidates+=("$c")
  fi
done

pick() {
  local p sz
  for p in "$@"; do
    [[ -n "$p" && -x "$p" ]] || continue
    sz=$(stat -c%s "$p" 2>/dev/null || echo 0)
    # Reject small alternates shims; real cpython is usually multi‑MB
    if [[ "$sz" -lt 1048576 ]]; then
      continue
    fi
    if ! file -b "$p" 2>/dev/null | grep -q ELF; then
      continue
    fi
    # Reject if CPython points at a Cursor AppImage in sys.executable
    if ! "$p" -c "import sys; s = sys.executable or ''; raise SystemExit(0 if s and 'AppImage' not in s else 1)" 2>/dev/null; then
      continue
    fi
    echo "$p"
    return 0
  done
  return 1
}

P=$(pick "${candidates[@]}") || {
  echo "Could not find a real CPython (or yours reports Cursor in sys.executable)." >&2
  echo "Set PYTHON_BOOTSTRAP to a full python path, e.g.:" >&2
  echo "  PYTHON_BOOTSTRAP=/path/to/python3.12 $0" >&2
  echo "On Fedora, install: sudo dnf install python3.12" >&2
  echo "or use a python.org or pyenv 3.11+ build." >&2
  exit 1
}

echo "Using: $P"
"$P" -m venv .venv
.venv/bin/pip install -U pip
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/python -c "import pytest; import httpx"  # sanity: deps on venv’s real interpreter
echo "OK: .venv is ready. Run: source .venv/bin/activate && python -m pytest -q"
