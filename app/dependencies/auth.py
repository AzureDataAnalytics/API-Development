"""
app/dependencies/auth.py
------------------------
API Key authentication dependency (Option 1).

All protected routes declare `dependencies=[Depends(require_api_key)]`.
The key is read from the `X-API-Key` request header and validated against
the comma-separated list stored in `API_KEYS` (.env / environment variable).

Swagger UI (/docs) shows an "Authorize" button where you can enter a key
and test all endpoints interactively without adding the header manually.
"""
from __future__ import annotations

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.config import get_settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Identical message for missing vs. wrong key — do not reveal which check failed.
_DENY_MSG = "Invalid or missing API key. Pass your key in the X-API-Key header."


def require_api_key(key: str | None = Security(_api_key_header)) -> str:
    """
    FastAPI dependency that enforces API key authentication.

    Raises 401 when the key is absent or not in the configured key set.
    Returns the validated key string on success (can be used downstream to
    identify the caller if keys are named/scoped).
    """
    settings = get_settings()
    valid_keys: set[str] = {k.strip() for k in settings.api_keys.split(",") if k.strip()}

    if not key or key not in valid_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": _DENY_MSG},
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return key
