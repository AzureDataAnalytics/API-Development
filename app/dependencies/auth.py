"""
app/dependencies/auth.py
------------------------
API Key authentication dependency (Option 1).

Key loading priority:
  1. Azure Key Vault  — if AZURE_KEYVAULT_URL is set (production)
     Reads every enabled secret whose name starts with "api-key-"
     e.g. api-key-admin, api-key-mobile, api-key-reporting
  2. API_KEYS env var — comma-separated fallback for local development

Keys are loaded once on first request and cached for the process lifetime.
Restart the API to pick up newly added or revoked secrets from Key Vault.

Swagger UI (/docs) shows an "Authorize" button — enter any valid key there
to test all endpoints interactively without setting the header manually.
"""
from __future__ import annotations

import logging
from functools import lru_cache

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.config import get_settings

logger = logging.getLogger(__name__)

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Same message for missing vs wrong key — never reveal which check failed.
_DENY_MSG = "Invalid or missing API key. Pass your key in the X-API-Key header."


@lru_cache(maxsize=1)
def _load_valid_keys() -> frozenset[str]:
    """
    Load the set of valid API keys — called once and cached for process lifetime.

    Production path  : fetches all enabled secrets named api-key-* from Azure
                       Key Vault using DefaultAzureCredential (Managed Identity
                       on Azure, Azure CLI credentials locally).
    Local dev path   : splits the API_KEYS environment variable by comma.
    """
    settings = get_settings()

    if settings.azure_keyvault_url:
        from azure.identity import DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient

        logger.info("Loading API keys from Key Vault: %s", settings.azure_keyvault_url)
        credential = DefaultAzureCredential()
        client = SecretClient(vault_url=settings.azure_keyvault_url, credential=credential)

        keys: set[str] = set()
        for prop in client.list_properties_of_secrets():
            if prop.name.startswith("api-key-") and prop.enabled:
                secret = client.get_secret(prop.name)
                if secret.value:
                    keys.add(secret.value)
                    logger.info("  loaded key for client '%s'", prop.name)

        if not keys:
            raise RuntimeError(
                "No api-key-* secrets found in Key Vault. "
                "Add at least one secret named api-key-<client>."
            )
        logger.info("Loaded %d API key(s) from Key Vault", len(keys))
        return frozenset(keys)

    # ── Local dev fallback ────────────────────────────────────────────────────
    if not settings.api_keys:
        raise RuntimeError(
            "No API keys configured. Set AZURE_KEYVAULT_URL (production) "
            "or API_KEYS (local dev) in your environment / .env file."
        )
    fallback = frozenset(k.strip() for k in settings.api_keys.split(",") if k.strip())
    logger.info("Loaded %d API key(s) from API_KEYS env var (local dev)", len(fallback))
    return fallback


def require_api_key(key: str | None = Security(_api_key_header)) -> str:
    """FastAPI dependency — raises 401 when the key is absent or unrecognised."""
    if not key or key not in _load_valid_keys():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": _DENY_MSG},
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return key
