from pathlib import Path

from feature_scaffold.cli import _load_config
from feature_scaffold.generator import ScaffoldGenerator
from feature_scaffold.models import (
    CapabilitiesConfig,
    DatabaseCapabilityConfig,
    DatabaseProvidersConfig,
    PostgresCapabilityConfig,
    ScaffoldConfig,
)


def test_deploy_workflow_contains_secret_validation_and_manifest_artifact(tmp_path: Path):
    config = _load_config(Path("examples/orders-feature.json"))
    generator = ScaffoldGenerator(Path("src/feature_scaffold/templates"))

    repo = generator.generate(config, tmp_path)

    workflows_dir = repo / ".github" / "workflows"

    dev_workflow = workflows_dir / "deploy.dev.yml"
    test_workflow = workflows_dir / "deploy.test.yml"
    prod_workflow = workflows_dir / "deploy.prod.yml"

    assert dev_workflow.exists()
    assert test_workflow.exists()
    assert prod_workflow.exists()

    content = dev_workflow.read_text(encoding="utf-8")

    assert "Validate required secrets" in content
    assert "AZURE_CLIENT_ID" in content
    assert "AZURE_TENANT_ID" in content
    assert "AZURE_SUBSCRIPTION_ID" in content

    assert "render-manifest.py" in content
    assert "validate-manifest.py" in content
    assert "render-registry-payload.py" in content

    assert "resolved-feature-manifest" in content
    assert "registry-payload-dev" in content

    assert "terraform init" in content
    assert "terraform apply" in content

    assert "azure/login@v2" in content

    assert "npm ci" in content
    assert "npm run build" in content

    assert "pip install -e ./backend" in content



def test_deploy_workflows_include_migration_step_when_postgres_migrations_enabled(tmp_path: Path) -> None:
    config = _load_config(Path("examples/orders-feature.json"))
    generator = ScaffoldGenerator(Path("src/feature_scaffold/templates"))

    repo = generator.generate(config, tmp_path)

    deploy_dev = (repo / ".github" / "workflows" / "deploy.dev.yml").read_text(encoding="utf-8")
    deploy_test = (repo / ".github" / "workflows" / "deploy.test.yml").read_text(encoding="utf-8")
    deploy_prod = (repo / ".github" / "workflows" / "deploy.prod.yml").read_text(encoding="utf-8")

    for content in (deploy_dev, deploy_test, deploy_prod):
        assert "Run database migrations" in content
        assert "bash scripts/run-migrations.sh" in content
        assert "Rollback hint for failed migrations" in content


def test_deploy_workflows_exclude_migration_step_when_postgres_migrations_disabled(tmp_path: Path) -> None:
    generator = ScaffoldGenerator(Path("src/feature_scaffold/templates"))

    config = ScaffoldConfig(
        feature_name="orders",
        display_name="Orders",
        base_path="/orders",
        capabilities=CapabilitiesConfig(
            database=DatabaseCapabilityConfig(
                enabled=True,
                targets=["api"],
                providers=DatabaseProvidersConfig(
                    postgresql=PostgresCapabilityConfig(
                        enabled=True,
                        orm=True,
                        migrations=False,
                    )
                ),
            ),
        ),
    )

    repo = generator.generate(config, tmp_path)

    deploy_dev = (repo / ".github" / "workflows" / "deploy.dev.yml").read_text(encoding="utf-8")
    deploy_test = (repo / ".github" / "workflows" / "deploy.test.yml").read_text(encoding="utf-8")
    deploy_prod = (repo / ".github" / "workflows" / "deploy.prod.yml").read_text(encoding="utf-8")

    for content in (deploy_dev, deploy_test, deploy_prod):
        assert "Run database migrations" not in content
        assert "bash scripts/run-migrations.sh" not in content