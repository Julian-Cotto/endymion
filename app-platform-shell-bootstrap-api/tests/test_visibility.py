from app.services.bootstrap_service import BootstrapService


def test_feature_visible_when_permissions_and_flags_match():
    service = BootstrapService.__new__(BootstrapService)
    manifest = {
        "authorization": {
            "requiredPermissions": ["orders.view"],
            "requiredFlags": ["orders.enabled"],
        }
    }

    assert service._is_visible(
        manifest=manifest,
        permissions=["orders.view", "inventory.view"],
        resolved_flags={"orders.enabled": True},
    )


def test_feature_hidden_when_flag_disabled():
    service = BootstrapService.__new__(BootstrapService)
    manifest = {
        "authorization": {
            "requiredPermissions": ["orders.view"],
            "requiredFlags": ["orders.enabled"],
        }
    }

    assert not service._is_visible(
        manifest=manifest,
        permissions=["orders.view"],
        resolved_flags={"orders.enabled": False},
    )
