"""
app/services/cosmos_service.py
------------------------------
Single entry point for every Cosmos DB read and write.

Partition key strategy
  orders     container  →  /customerId
  orderitems container  →  /orderId

Cross-partition queries are needed for orders when only orderId is known
(e.g. GET /orders/{orderId}). All item lookups use the orderId partition
key directly, which keeps RU cost low.

The module-level singleton (_service) avoids rebuilding a CosmosClient
on every HTTP request, which is expensive.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from azure.cosmos import CosmosClient, exceptions

from app.config import get_settings

logger = logging.getLogger(__name__)


# ── ID generators ─────────────────────────────────────────────────────────────

def _new_order_id() -> str:
    return f"ORD-{uuid.uuid4().hex[:8].upper()}"


def _new_item_id() -> str:
    return f"ITEM-{uuid.uuid4().hex[:8].upper()}"


# ── Service class ─────────────────────────────────────────────────────────────

class CosmosService:
    """All Cosmos DB operations for the Food Orders API."""

    def __init__(self) -> None:
        settings = get_settings()
        client = CosmosClient(
            url=settings.cosmos_endpoint,
            credential=settings.cosmos_key,
        )
        db = client.get_database_client(settings.cosmos_database)
        self._orders = db.get_container_client(settings.orders_container)
        self._items = db.get_container_client(settings.order_items_container)

    # ── Orders ────────────────────────────────────────────────────────────────

    def create_order(self, data: dict) -> dict:
        """Insert a new order document. Assigns a generated id and orderDate."""
        doc = {
            "id": _new_order_id(),
            "orderDate": datetime.now(timezone.utc).isoformat(),
            **data,
        }
        return self._orders.create_item(body=doc)

    def get_all_orders(self) -> list[dict]:
        """Return every order, newest first. Scans all partitions."""
        return list(
            self._orders.query_items(
                query="SELECT * FROM c ORDER BY c.orderDate DESC",
                enable_cross_partition_query=True,
            )
        )

    def get_order(self, order_id: str) -> Optional[dict]:
        """Find a single order by its id (cross-partition query)."""
        results = list(
            self._orders.query_items(
                query="SELECT * FROM c WHERE c.id = @id",
                parameters=[{"name": "@id", "value": order_id}],
                enable_cross_partition_query=True,
            )
        )
        return results[0] if results else None

    def update_order(self, order_id: str, fields: dict) -> Optional[dict]:
        """Merge supplied fields into the existing order and persist it."""
        doc = self.get_order(order_id)
        if doc is None:
            return None
        doc.update(fields)
        return self._orders.replace_item(item=order_id, body=doc)

    def delete_order(self, order_id: str) -> bool:
        """Delete the order and cascade-delete every child item."""
        doc = self.get_order(order_id)
        if doc is None:
            return False

        for item in self.get_items_for_order(order_id):
            try:
                self._items.delete_item(item=item["id"], partition_key=order_id)
            except exceptions.CosmosResourceNotFoundError:
                pass  # already gone — not an error worth raising

        self._orders.delete_item(item=order_id, partition_key=doc["customerId"])
        return True

    def get_order_with_items(self, order_id: str) -> Optional[dict]:
        """Return {"order": {...}, "items": [...]} or None if order is absent."""
        doc = self.get_order(order_id)
        if doc is None:
            return None
        return {"order": doc, "items": self.get_items_for_order(order_id)}

    # ── Order Items ───────────────────────────────────────────────────────────

    def create_item(self, order_id: str, data: dict) -> dict:
        """Add a new item to an existing order."""
        doc = {"id": _new_item_id(), "orderId": order_id, **data}
        return self._items.create_item(body=doc)

    def get_items_for_order(self, order_id: str) -> list[dict]:
        """All items for a given order — single-partition read, low RU cost."""
        return list(
            self._items.query_items(
                query="SELECT * FROM c WHERE c.orderId = @order_id",
                parameters=[{"name": "@order_id", "value": order_id}],
                partition_key=order_id,
            )
        )

    def get_item(self, order_id: str, item_id: str) -> Optional[dict]:
        """Read a single item by id; return None if absent."""
        try:
            return self._items.read_item(item=item_id, partition_key=order_id)
        except exceptions.CosmosResourceNotFoundError:
            return None

    def update_item(self, order_id: str, item_id: str, fields: dict) -> Optional[dict]:
        """Merge supplied fields into the existing item and persist it."""
        doc = self.get_item(order_id, item_id)
        if doc is None:
            return None
        doc.update(fields)
        return self._items.replace_item(item=item_id, body=doc)

    def delete_item(self, order_id: str, item_id: str) -> bool:
        """Delete a single item. Returns False if the item does not exist."""
        if self.get_item(order_id, item_id) is None:
            return False
        self._items.delete_item(item=item_id, partition_key=order_id)
        return True


# ── Module-level singleton ────────────────────────────────────────────────────

_service: Optional[CosmosService] = None


def get_cosmos_service() -> CosmosService:
    """
    Dependency-injection factory used by FastAPI routes.
    Builds the CosmosClient once and reuses it for every request.
    """
    global _service
    if _service is None:
        _service = CosmosService()
    return _service
