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

    model_config = {"env_file": ".env"}


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance. Re-used across the app lifetime."""
    return Settings()
