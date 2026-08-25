import json
from pathlib import Path

from feature_scaffold.generator import ScaffoldGenerator
from feature_scaffold.models import ScaffoldConfig


def test_generated_manifest_has_required_contract_fields(tmp_path: Path) -> None:
    templates_dir = Path(__file__).parent.parent / "src" / "feature_scaffold" / "templates"
    repo_dir = ScaffoldGenerator(templates_dir=templates_dir).generate(
        ScaffoldConfig(feature_name="orders", display_name="Orders", base_path="/orders"),
        tmp_path,
    )

    manifest = json.loads((repo_dir / "contracts" / "feature-manifest.json").read_text(encoding="utf-8"))

    assert manifest["featureKey"] == "orders"
    assert manifest["basePath"] == "/orders"
    assert "frontend" in manifest
    assert "backend" in manifest
    assert "auth" in manifest
    assert "registry" in manifest
    assert "workers" in manifest
    assert manifest["frontend"]["mountFunction"] == "mount"