"""Shared helpers for integration-style tests."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]


def cli_python_executable() -> str:
    """Interpreter used to spawn `python -m feature_scaffold.cli` in tests.

    When the test runner is embedded in an IDE, ``sys.executable`` may point at a
    non-Python binary (e.g. an AppImage). Prefer the project venv or ``python3``.
    """
    override = os.environ.get("FEATURE_SCAFFOLD_TEST_PYTHON")
    if override:
        return override
    venv_py = _PROJECT_ROOT / ".venv" / "bin" / "python"
    if venv_py.is_file():
        return str(venv_py)
    for name in ("python3.12", "python3", "python"):
        found = shutil.which(name)
        if found:
            return found
    exe = sys.executable or ""
    p = Path(exe)
    # Embedded runners may set sys.executable to a non-Python path (e.g. missing AppImage).
    if exe.lower().endswith(".appimage") or (exe and not p.is_file()):
        found = shutil.which("python3") or shutil.which("python")
        if found:
            return found
    return exe
