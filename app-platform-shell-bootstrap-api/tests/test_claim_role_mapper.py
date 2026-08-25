from app.services.claim_role_mapper import roles_from_claims


class FakeSettings:
    auth_roles_claim = "roles"
    auth_groups_claim = "groups"
    auth_scope_claim = "scp"
    auth_wids_claim = "wids"


def test_roles_from_direct_roles_claim():
    payload = {
        "roles": ["orders.view", "catalog.view"],
    }

    result = roles_from_claims(payload, FakeSettings())

    assert result == ["orders.view", "catalog.view"]


def test_roles_from_groups_claim_are_not_mapped_to_roles():
    payload = {
        "groups": ["group-orders", "group-devs"],
    }

    result = roles_from_claims(payload, FakeSettings())

    assert result == []


def test_roles_from_scope_claim_are_not_mapped_to_roles():
    payload = {
        "scp": "orders.read catalog.read",
    }

    result = roles_from_claims(payload, FakeSettings())

    assert result == []


def test_roles_from_wids_claim_are_not_mapped_to_roles():
    payload = {
        "wids": ["wid-admin"],
    }

    result = roles_from_claims(payload, FakeSettings())

    assert result == []


def test_roles_from_mixed_claims_use_roles_claim_only_and_dedupe():
    payload = {
        "roles": ["orders.view", "orders.view", "catalog.view"],
        "groups": ["group-devs"],
        "scp": "orders.read",
        "wids": ["wid-admin"],
    }

    result = roles_from_claims(payload, FakeSettings())

    assert result == ["orders.view", "catalog.view"]


def test_unknown_direct_roles_pass_through_for_entra_role_source_of_truth():
    payload = {
        "roles": ["unknown-role"],
        "groups": ["unknown-group"],
        "scp": "unknown.scope",
        "wids": ["unknown-wid"],
    }

    result = roles_from_claims(payload, FakeSettings())

    assert result == ["unknown-role"]