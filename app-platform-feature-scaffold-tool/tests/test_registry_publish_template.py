from pathlib import Path

from feature_scaffold.cli import _load_config
from feature_scaffold.generator import ScaffoldGenerator


def test_deploy_workflow_renders_and_publishes_registry_payload(tmp_path: Path) -> None:
    templates_dir = Path("src/feature_scaffold/templates")
    config = _load_config(Path("examples/orders-feature.json"))

    repo_dir = ScaffoldGenerator(templates_dir=templates_dir).generate(config, tmp_path)

    workflows_dir = repo_dir / ".github" / "workflows"

    dev_workflow = workflows_dir / "deploy.dev.yml"
    test_workflow = workflows_dir / "deploy.test.yml"
    prod_workflow = workflows_dir / "deploy.prod.yml"

    assert dev_workflow.exists()
    assert test_workflow.exists()
    assert prod_workflow.exists()

    for workflow_path in [dev_workflow, test_workflow, prod_workflow]:
        content = workflow_path.read_text(encoding="utf-8")

        assert "Render registry payload" in content
        assert "registry-payload" in content
        assert "--data-binary @build/registry-payload.json" in content