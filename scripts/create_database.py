"""
scripts/create_database.py
--------------------------
Idempotent setup script: creates FoodOrdersDB and both containers if absent.
Safe to run multiple times — existing resources are left untouched.

Usage:
    python scripts/create_database.py
"""
from __future__ import annotations

import os
import sys

# Allow running from the repo root without installing the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from azure.cosmos import CosmosClient, PartitionKey, exceptions
from dotenv import load_dotenv

from app.config import get_settings

load_dotenv()


def create_infrastructure() -> None:
    """Create the Cosmos DB database and both containers."""
    settings = get_settings()

    print(f"\nConnecting to: {settings.cosmos_endpoint}")
    client = CosmosClient(url=settings.cosmos_endpoint, credential=settings.cosmos_key)

    # ── Database ──────────────────────────────────────────────────────────────
    try:
        db = client.create_database(id=settings.cosmos_database)
        print(f"  [+] Created database: {settings.cosmos_database}")
    except exceptions.CosmosResourceExistsError:
        db = client.get_database_client(settings.cosmos_database)
        print(f"  [=] Database already exists: {settings.cosmos_database}")

    # ── orders container (/customerId) ────────────────────────────────────────
    try:
        db.create_container(
            id=settings.orders_container,
            partition_key=PartitionKey(path="/customerId"),
        )
        print(f"  [+] Created container '{settings.orders_container}'  (partition: /customerId)")
    except exceptions.CosmosResourceExistsError:
        print(f"  [=] Container already exists: {settings.orders_container}")

    # ── orderitems container (/orderId) ───────────────────────────────────────
    try:
        db.create_container(
            id=settings.order_items_container,
            partition_key=PartitionKey(path="/orderId"),
        )
        print(f"  [+] Created container '{settings.order_items_container}'  (partition: /orderId)")
    except exceptions.CosmosResourceExistsError:
        print(f"  [=] Container already exists: {settings.order_items_container}")

    print("\nInfrastructure ready. Run seed_data.py to load sample data.\n")


if __name__ == "__main__":
    create_infrastructure()
