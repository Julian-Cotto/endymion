from pathlib import Path

from feature_scaffold.generator import ScaffoldGenerator
from feature_scaffold.models import ScaffoldConfig


def test_generator_creates_dev_test_prod_tfvars_examples(tmp_path: Path) -> None:
    templates_dir = Path(__file__).parent.parent / "src" / "feature_scaffold" / "templates"
    generator = ScaffoldGenerator(templates_dir=templates_dir)

    config = ScaffoldConfig(
        feature_name="orders",
        display_name="Orders",
        base_path="/orders",
    )

    repo_dir = generator.generate(config, tmp_path)

    assert (repo_dir / "infra/terraform/dev.tfvars.example").exists()
    assert (repo_dir / "infra/terraform/test.tfvars.example").exists()
    assert (repo_dir / "infra/terraform/prod.tfvars.example").exists()