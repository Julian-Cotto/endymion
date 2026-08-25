from dataclasses import dataclass

@dataclass(slots=True)
class FeatureRuntimeConfig:
    feature_key: str
    base_path: str
    api_base_path: str


def get_runtime_config() -> FeatureRuntimeConfig:
    return FeatureRuntimeConfig(
        feature_key="lead-locator",
        base_path="/leads",
        api_base_path="/api/leads",
    )