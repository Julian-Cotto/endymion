from __future__ import annotations

import httpx
from fastapi import HTTPException, status


class RegistryClient:
    def __init__(
        self,
        base_url: str | object,
        read_token: str | None = None,
        timeout_seconds: float = 10.0,
    ):
        if not isinstance(base_url, str):
            base_url = getattr(base_url, "registry_base_url", "http://localhost:8010")

        self.base_url = base_url.rstrip("/")
        self.read_token = read_token
        self.timeout_seconds = timeout_seconds

    async def get_active_features(self, environment: str) -> list[dict]:
        url = f"{self.base_url}/api/runtime/features"

        headers = {"Accept": "application/json"}

        if self.read_token:
            headers["Authorization"] = f"Bearer {self.read_token}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(
                    url,
                    params={"environment": environment},
                    headers=headers,
                )
        except httpx.ConnectError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    f"Registry is unreachable at {self.base_url}. "
                    "Start the registry service or fix REGISTRY_BASE_URL. "
                    f"({exc!s})"
                ),
            ) from exc
        except httpx.TimeoutException as exc:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=(
                    f"Registry request timed out after {self.timeout_seconds}s: {url} ({exc!s})"
                ),
            ) from exc
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Registry request failed for {url}: {exc!s}",
            ) from exc

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            body_preview = (exc.response.text or "")[:200]
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=(
                    f"Registry returned HTTP {exc.response.status_code} for {url}. "
                    f"Preview: {body_preview!r}"
                ),
            ) from exc

        return self._extract_feature_list(response.json())

    # RESTORED — tests depend on this
    def _extract_feature_list(self, payload) -> list[dict]:
        if isinstance(payload, list):
            return payload

        if isinstance(payload, dict):
            features = payload.get("features")
            if isinstance(features, list):
                return features

        raise ValueError("Invalid registry response shape.")