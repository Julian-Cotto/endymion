class RegistryError(Exception):
    pass


class ValidationError(RegistryError):
    pass


class NotFoundError(RegistryError):
    pass


class ConflictError(RegistryError):
    pass


class AuthorizationError(RegistryError):
    pass
