from dataclasses import dataclass

@dataclass(slots=True)
class FeatureRuntimeConfig:
    feature_key: str
    base_path: str
    api_base_path: str


def get_runtime_config() -> FeatureRuntimeConfig:
    return FeatureRuntimeConfig(
        feature_key="reports-layering",
        base_path="/reports",
        api_base_path="/api/reports",
    )