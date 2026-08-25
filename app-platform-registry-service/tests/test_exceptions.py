from app.exceptions import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
    RegistryError,
    ValidationError,
)


def test_registry_error_hierarchy():
    assert issubclass(ValidationError, RegistryError)
    assert issubclass(NotFoundError, RegistryError)
    assert issubclass(ConflictError, RegistryError)
    assert issubclass(AuthorizationError, RegistryError)
