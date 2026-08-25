from __future__ import annotations

from pathlib import Path


def write_text_file(base_dir: Path, relative_path: str, content: str) -> None:
    path = base_dir / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
