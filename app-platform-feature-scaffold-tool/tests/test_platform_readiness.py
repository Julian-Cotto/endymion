from pathlib import Path

from feature_scaffold.cli import _load_config
from feature_scaffold.generator import ScaffoldGenerator


def test_generated_repo_contains_platform_contract_files(tmp_path: Path) -> None:
    templates_dir = Path("src/feature_scaffold/templates")
    config = _load_config(Path("examples/orders-feature.json"))

    repo_dir = ScaffoldGenerator(templates_dir=templates_dir).generate(config, tmp_path)

    # --- Contracts & scripts ---
    assert (repo_dir / "contracts" / "feature-manifest.json").exists()
    assert (repo_dir / "manifest.schema.json").exists()
    assert (repo_dir / "scripts" / "render-manifest.py").exists()
    assert (repo_dir / "scripts" / "validate-manifest.py").exists()
    assert (repo_dir / "scripts" / "render-registry-payload.py").exists()

    # --- GitHub workflows (updated to multi-env model) ---
    workflows_dir = repo_dir / ".github" / "workflows"

    assert (workflows_dir / "deploy.dev.yml").exists()
    assert (workflows_dir / "deploy.test.yml").exists()
    assert (workflows_dir / "deploy.prod.yml").exists()