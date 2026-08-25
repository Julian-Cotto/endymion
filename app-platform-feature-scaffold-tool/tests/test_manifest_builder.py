import json

from feature_scaffold.manifest_builder import build_feature_manifest
from feature_scaffold.models import ScaffoldConfig
from feature_scaffold.normalizers import normalize_config

def test_build_feature_manifest_contains_expected_fields() -> None:
    manifest = json.loads(build_feature_manifest(normalize_config(ScaffoldConfig(feature_name="orders", display_name="Orders", base_path="/orders"))))
    assert manifest["featureKey"] == "orders"
    assert manifest["basePath"] == "/orders"
    assert manifest["frontend"]["enabled"] is True
