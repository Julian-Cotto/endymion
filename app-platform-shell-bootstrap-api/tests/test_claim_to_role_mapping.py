from app.core.jwt_auth import build_authenticated_user_from_claims


class FakeSettings:
    auth_roles_claim = "roles"
    auth_groups_claim = "groups"
    auth_scope_claim = "scp"
    auth_wids_claim = "wids"

    auth_user_id_claim = "sub"
    auth_user_name_claim = "name"
    auth_email_claim = "email"


def test_scope_does_not_map_to_role():
    payload = {
        "sub": "u1",
        "name": "Test",
        "email": "test@example.com",
        "scp": "orders.read",
    }

    user = build_authenticated_user_from_claims(payload, FakeSettings())

    assert user.roles == []


def test_direct_permission_shaped_role_passes_through():
    payload = {
        "sub": "u1",
        "name": "Test",
        "email": "test@example.com",
        "roles": ["orders.view"],
    }

    user = build_authenticated_user_from_claims(payload, FakeSettings())

    assert user.roles == ["orders.view"]