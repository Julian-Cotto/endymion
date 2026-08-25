from pathlib import Path

from feature_scaffold.models import PlannedFile
from feature_scaffold.planner_diff import compute_plan_diff


def test_modified_when_content_differs(tmp_path: Path) -> None:
    p = tmp_path / "file.txt"
    p.write_text("current", encoding="utf-8")
    plan = [PlannedFile("file.txt", literal_content="x")]
    changes = compute_plan_diff(tmp_path, plan, {"file.txt": "expected"})
    assert any(a == "MODIFIED" for a, path in changes if path == "file.txt")
