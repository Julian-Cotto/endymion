from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class AuthenticatedUser:
    id: str
    display_name: str | None
    email: str | None
    roles: list[str]
    claims: dict[str, Any]