import json
from pathlib import Path

from app.schemas.registry_manifest import RegistryManifest
from app.services.registry_client import RegistryClient
from app.services.registry_manifest_mapper import (
    registry_manifest_to_bootstrap_feature,
    registry_manifest_to_runtime_feature,
)


class FakeSettings:
    registry_base_url = "http://registry.local"


def _load_fixture(name: str):
    path = Path("tests/fixtures") / name
    return json.loads(path.read_text(encoding="utf-8"))


def test_single_feature_fixture_validates_and_maps() -> None:
    client = RegistryClient(FakeSettings())
    payload = _load_fixture("registry_payload_single_feature.json")

    extracted = client._extract_feature_list(payload)
    assert len(extracted) == 1

    manifest = RegistryManifest.model_validate(extracted[0])

    bootstrap_feature = registry_manifest_to_bootstrap_feature(manifest)
    runtime_feature = registry_manifest_to_runtime_feature(manifest)

    assert bootstrap_feature.featureKey == "orders"
    assert bootstrap_feature.frontend.entryUrl == "http://localhost:3200/src/bootstrap-entry.tsx"
    assert bootstrap_feature.backend.apiBaseUrl == "http://localhost:8100/api/orders"

    assert runtime_feature.featureKey == "orders"
    assert runtime_feature.frontend.entryUrl == "http://localhost:3200/src/bootstrap-entry.tsx"
    assert runtime_feature.backend.apiBaseUrl == "http://localhost:8100/api/orders"


def test_two_feature_fixture_extracts_both_features() -> None:
    client = RegistryClient(FakeSettings())
    payload = _load_fixture("registry_payload_two_features.json")

    extracted = client._extract_feature_list(payload)
    assert len(extracted) == 2

    manifests = [RegistryManifest.model_validate(item) for item in extracted]

    assert manifests[0].featureKey == "orders"
    assert manifests[1].featureKey == "catalog"

    bootstrap_features = [
        registry_manifest_to_bootstrap_feature(manifest)
        for manifest in manifests
    ]
    runtime_features = [
        registry_manifest_to_runtime_feature(manifest)
        for manifest in manifests
    ]

    assert bootstrap_features[0].backend.apiBaseUrl == "http://localhost:8100/api/orders"
    assert bootstrap_features[1].backend.apiBaseUrl == "http://localhost:8200/api/catalog"

    assert runtime_features[0].frontend.entryUrl == "http://localhost:3200/src/bootstrap-entry.tsx"
    assert runtime_features[1].frontend.entryUrl == "http://localhost:3300/src/bootstrap-entry.tsx"