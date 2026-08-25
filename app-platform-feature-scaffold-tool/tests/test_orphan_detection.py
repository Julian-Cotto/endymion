import json
from pathlib import Path

from feature_scaffold.models import PlannedFile
from feature_scaffold.planner_diff import compute_plan_diff


def test_orphan_when_managed_file_not_in_plan(tmp_path: Path) -> None:
    orphan = tmp_path / "old" / "path.txt"
    orphan.parent.mkdir(parents=True, exist_ok=True)
    orphan.write_text("x", encoding="utf-8")

    (tmp_path / "scaffold.metadata.json").write_text(
        json.dumps({"managedFiles": {"old/path.txt": "replace"}}),
        encoding="utf-8",
    )

    (tmp_path / "README.md").write_text("x", encoding="utf-8")
    plan: list[PlannedFile] = [PlannedFile("README.md", literal_content="x")]

    changes = compute_plan_diff(tmp_path, plan, {})
    assert any(a == "ORPHAN" and p == "old/path.txt" for a, p in changes)
