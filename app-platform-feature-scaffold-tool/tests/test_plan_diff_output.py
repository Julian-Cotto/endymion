from pathlib import Path

from feature_scaffold.models import PlannedFile
from feature_scaffold.planner_diff import compute_plan_diff


def test_compute_plan_diff_create_when_missing(tmp_path: Path) -> None:
    plan = [PlannedFile("README.md", "x.j2")]
    changes = compute_plan_diff(tmp_path, plan, {"README.md": "hello"})
    assert ("CREATE", "README.md") in changes
