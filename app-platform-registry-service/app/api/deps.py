from fastapi import Depends, Request

from app.core.security import Principal, get_principal_from_request, require_role


def get_principal(request: Request) -> Principal:
    return get_principal_from_request(request)


def require_runtime_read(principal: Principal = Depends(get_principal)) -> Principal:
    require_role(principal, "registry.runtime.read")
    return principal


def require_release_write(principal: Principal = Depends(get_principal)) -> Principal:
    require_role(principal, "registry.release.write")
    return principal


def require_release_activate(principal: Principal = Depends(get_principal)) -> Principal:
    require_role(principal, "registry.release.activate")
    return principal
