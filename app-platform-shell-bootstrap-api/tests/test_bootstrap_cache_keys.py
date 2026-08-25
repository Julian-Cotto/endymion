from app.services.bootstrap_service import BootstrapService


class FakeService:
    app_env = "test"


def test_bootstrap_cache_key_is_versioned():
    key = BootstrapService._build_bootstrap_cache_key(
        FakeService(),
        "u1",
        ["orders.view", "catalog.view"],
    )

    assert key == "bootstrap:v3:test:u1:catalog.view|orders.view"


def test_runtime_cache_key_is_versioned():
    key = BootstrapService._build_runtime_cache_key(
        FakeService(),
        "u1",
        ["orders.view", "catalog.view"],
    )

    assert key == "runtime:v3:test:u1:catalog.view|orders.view"