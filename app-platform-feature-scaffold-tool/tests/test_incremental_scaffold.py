import json
from pathlib import Path

from feature_scaffold.generator import ScaffoldGenerator
from feature_scaffold.models import ScaffoldConfig
from feature_scaffold.planner_diff import compute_plan_diff
from feature_scaffold.planners import build_file_plan
from feature_scaffold.normalizers import normalize_config


def test_generate_writes_metadata_and_plan_matches(tmp_path: Path) -> None:
    templates_dir = Path(__file__).parent.parent / "src" / "feature_scaffold" / "templates"
    cfg = ScaffoldConfig(feature_name="orders", display_name="Orders", base_path="/orders")
    repo_dir = ScaffoldGenerator(templates_dir=templates_dir).generate(cfg, tmp_path)

    meta_path = repo_dir / "scaffold.metadata.json"
    assert meta_path.is_file()
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["featureKey"] == "orders"
    assert "managedFiles" in meta

    normalized = normalize_config(cfg)
    plan = build_file_plan(normalized)
    changes = compute_plan_diff(repo_dir, plan, {})
    assert all(action != "ORPHAN" for action, _ in changes)
