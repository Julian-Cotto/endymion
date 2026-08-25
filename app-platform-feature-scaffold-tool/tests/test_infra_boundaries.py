from pathlib import Path

from feature_scaffold.generator import ScaffoldGenerator
from feature_scaffold.models import ScaffoldConfig


def test_infra_readme_mentions_feature_local_ownership(tmp_path: Path) -> None:
    templates_dir = Path(__file__).parent.parent / "src" / "feature_scaffold" / "templates"
    repo_dir = ScaffoldGenerator(templates_dir=templates_dir).generate(
        ScaffoldConfig(feature_name="orders", display_name="Orders", base_path="/orders"),
        tmp_path,
    )

    readme = (repo_dir / "infra" / "terraform" / "README.md").read_text(encoding="utf-8")
    assert "feature-local" in readme.lower()