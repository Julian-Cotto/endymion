"""CLI JSON output is covered indirectly via planner_diff + run_plan integration."""

from pathlib import Path

from feature_scaffold.models import PlannedFile
from feature_scaffold.planner_diff import compute_plan_diff


def test_diff_summary_counts(tmp_path: Path) -> None:
    plan = [PlannedFile("a.txt", literal_content="a")]
    (tmp_path / "a.txt").write_text("b", encoding="utf-8")
    changes = compute_plan_diff(tmp_path, plan, {"a.txt": "a"})
    actions = [a for a, _ in changes]
    assert "MODIFIED" in actions
