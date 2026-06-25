"""
app/routes/items.py
-------------------
CRUD endpoints for Order Items, nested under /api/orders/{order_id}/items.

All handlers verify the parent order exists before touching items so that
callers get a meaningful 404 rather than an empty list.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.models.order_item import OrderItemCreate, OrderItemUpdate
from app.services.cosmos_service import CosmosService, get_cosmos_service

router = APIRouter(prefix="/api/orders/{order_id}/items", tags=["Order Items"])


def _order_404(order_id: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"message": f"Order '{order_id}' not found"},
    )


def _item_404(order_id: str, item_id: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"message": f"Item '{item_id}' not found in order '{order_id}'"},
    )


def _require_order(order_id: str, cosmos: CosmosService) -> None:
    """Raise 404 when the parent order does not exist."""
    if cosmos.get_order(order_id) is None:
        raise _order_404(order_id)


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Add an item to an order",
)
def create_item(
    order_id: str,
    payload: OrderItemCreate,
    cosmos: CosmosService = Depends(get_cosmos_service),
) -> dict:
    """
    Add a food item to an existing order.

    - Assigns a unique **ITEM-XXXXXXXX** id
    - Sets **orderId** to the path parameter automatically
    """
    _require_order(order_id, cosmos)
    return cosmos.create_item(order_id, payload.model_dump())


@router.get(
    "/",
    summary="List all items for an order",
    response_description="Array of order item documents",
)
def get_items(
    order_id: str,
    cosmos: CosmosService = Depends(get_cosmos_service),
) -> list:
    """Return every item belonging to the given order."""
    _require_order(order_id, cosmos)
    return cosmos.get_items_for_order(order_id)


@router.get(
    "/{item_id}",
    summary="Get a single order item",
    response_description="The order item document",
)
def get_item(
    order_id: str,
    item_id: str,
    cosmos: CosmosService = Depends(get_cosmos_service),
) -> dict:
    """Return one item by its id."""
    item = cosmos.get_item(order_id, item_id)
    if item is None:
        raise _item_404(order_id, item_id)
    return item


@router.put(
    "/{item_id}",
    summary="Update an order item",
    response_description="The updated order item document",
)
def update_item(
    order_id: str,
    item_id: str,
    payload: OrderItemUpdate,
    cosmos: CosmosService = Depends(get_cosmos_service),
) -> dict:
    """
    Partial update — only fields included in the request body are changed.
    Fields omitted (or set to null) are left as-is.
    """
    fields = {k: v for k, v in payload.model_dump().items() if v is not None}
    updated = cosmos.update_item(order_id, item_id, fields)
    if updated is None:
        raise _item_404(order_id, item_id)
    return updated


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a single order item",
)
def delete_item(
    order_id: str,
    item_id: str,
    cosmos: CosmosService = Depends(get_cosmos_service),
) -> Response:
    """
    Delete one item. Does not affect sibling items or the parent order.
    Returns 204 No Content on success.
    """
    if not cosmos.delete_item(order_id, item_id):
        raise _item_404(order_id, item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
