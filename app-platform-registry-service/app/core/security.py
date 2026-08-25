from fastapi import HTTPException, Request, status

from app.core.config import get_settings


class Principal:
    def __init__(self, subject: str, roles: list[str], audiences: list[str], claims: dict):
        self.subject = subject
        self.roles = roles
        self.audiences = audiences
        self.claims = claims


def _extract_bearer(request: Request) -> str | None:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    return None


def _mock_decode_for_dev(token: str) -> dict:
    # Placeholder for real Entra JWT validation and JWKS verification.
    if token == "shell-read-token":
        return {
            "sub": "shell-runtime",
            "aud": "api://portal-registry-runtime",
            "roles": ["registry.runtime.read"],
        }
    if token == "pipeline-write-token":
        return {
            "sub": "feature-pipeline-orders",
            "aud": "api://portal-registry-admin",
            "roles": ["registry.release.write", "registry.release.activate"],
            "feature_keys": ["orders"],
        }
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid bearer token")


def get_principal_from_request(request: Request) -> Principal:
    settings = get_settings()

    if settings.auth_disabled:
        return Principal(
            subject="local-dev",
            roles=[
                "registry.runtime.read",
                "registry.release.write",
                "registry.release.activate",
            ],
            audiences=[
                "api://portal-registry-runtime",
                "api://portal-registry-admin",
            ],
            claims={"feature_keys": ["*"]},
        )

    token = _extract_bearer(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")

    claims = _mock_decode_for_dev(token)
    aud = claims.get("aud")
    audiences = [aud] if isinstance(aud, str) else (aud or [])

    return Principal(
        subject=claims.get("sub", "unknown"),
        roles=claims.get("roles", []),
        audiences=audiences,
        claims=claims,
    )


def require_role(principal: Principal, role: str) -> None:
    if role not in principal.roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"missing role: {role}")


def require_feature_scope(principal: Principal, feature_key: str) -> None:
    allowed = principal.claims.get("feature_keys", [])
    if "*" in allowed:
        return
    if feature_key not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="feature scope not allowed")
