"""Pydantic schemas for anonymous session endpoints.

Enforces strict field boundaries: raw tokens, hashes, and internal filesystem paths
are never serialized into API responses.
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class SessionResponse(BaseModel):
    """Public metadata representation of an active anonymous session."""
    id: str
    created_at: datetime
    expires_at: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class SessionResetResponse(BaseModel):
    """Confirmation payload returned upon session revocation."""
    status: str
    message: str
