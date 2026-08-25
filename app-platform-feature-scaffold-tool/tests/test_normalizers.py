from feature_scaffold.models import CacheCapabilityConfig, CacheProvidersConfig, CapabilitiesConfig, MemoryCacheCapabilityConfig, RedisCacheCapabilityConfig, ScaffoldConfig
from feature_scaffold.normalizers import normalize_config

def test_normalize_config_generates_expected_names() -> None:
    normalized = normalize_config(ScaffoldConfig(feature_name="orders-management", display_name="Orders", base_path="/orders"))
    assert normalized.names.feature_key == "orders-management"
    assert normalized.names.repo_name == "feature-orders-management"
    assert normalized.names.python_package_name == "orders_management_service"


def test_normalize_cache_capability() -> None:
    config = ScaffoldConfig(
        feature_name="orders",
        display_name="Orders",
        base_path="/orders",
        capabilities=CapabilitiesConfig(
            cache=CacheCapabilityConfig(
                enabled=True,
                targets=["api", "jobs", "listeners"],
                providers=CacheProvidersConfig(
                    memory=MemoryCacheCapabilityConfig(enabled=True),
                    redis=RedisCacheCapabilityConfig(enabled=False),
                ),
            )
        ),
    )

    normalized = normalize_config(config)

    assert normalized.cache_enabled is True
    assert normalized.cache_targets == ["api", "jobs", "listeners"]
    assert normalized.memory_cache_enabled is True
    assert normalized.redis_enabled is False