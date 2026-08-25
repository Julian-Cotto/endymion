from pydantic import BaseModel


class UserSummary(BaseModel):
    id: str
    displayName: str | None = None
    email: str | None = None
