from app.core.auth import AuthenticatedUser
from app.services.permissions import PermissionService


class FakeSettings:
    platform_admin_role = "platform.admin"


def test_orders_view_role_maps_correctly():
    user = AuthenticatedUser(
        id="u1",
        display_name="Test",
        email="test@example.com",
        roles=["orders.view"],
        claims={},
    )

    svc = PermissionService(FakeSettings())

    assert svc.get_permissions(user) == ["orders.view"]


def test_developer_role_no_longer_expands_to_feature_permissions():
    user = AuthenticatedUser(
        id="u1",
        display_name="Test",
        email="test@example.com",
        roles=["developer"],
        claims={},
    )

    svc = PermissionService(FakeSettings())

    assert svc.get_permissions(user) == ["developer"]


def test_platform_admin_maps_to_wildcard():
    user = AuthenticatedUser(
        id="u1",
        display_name="Test",
        email="test@example.com",
        roles=["platform.admin"],
        claims={},
    )

    svc = PermissionService(FakeSettings())

    assert svc.get_permissions(user) == ["*"]