"""
app/config.py
-------------
Application settings loaded from environment variables (or a .env file).
Uses pydantic-settings so every value is type-validated at startup.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    cosmos_endpoint: str
    cosmos_key: str
    cosmos_database: str = "FoodOrdersDB"
    orders_container: str = "orders"
    order_items_container: str = "orderitems"

    # Azure Blob Storage — item images
    storage_connection_string: str
    storage_image_container: str = "item-images"

    # Authentication — Option 1: API Keys
    # Production: set AZURE_KEYVAULT_URL — keys are fetched from Key Vault secrets
    #             named api-key-<client> (e.g. api-key-admin, api-key-mobile).
    # Local dev:  leave AZURE_KEYVAULT_URL empty and set API_KEYS instead.
    azure_keyvault_url: str = ""
    api_keys: str = ""   # fallback for local dev when azure_keyvault_url is not set

    model_config = {"env_file": ".env"}


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance. Re-used across the app lifetime."""
    return Settings()
