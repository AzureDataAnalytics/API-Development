"""
app/routes/orders.py
--------------------
CRUD endpoints for the Order resource.

All handlers are synchronous (def, not async def). FastAPI automatically
runs sync handlers in a thread pool, which is the correct approach when
using the synchronous azure-cosmos SDK.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.models.order import OrderCreate, OrderUpdate
from app.services.cosmos_service import CosmosService, get_cosmos_service

router = APIRouter(prefix="/api/orders", tags=["Orders"])


def _404(order_id: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"message": f"Order '{order_id}' not found"},
    )


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new order",
    response_description="The newly created order document",
)
def create_order(
    payload: OrderCreate,
    cosmos: CosmosService = Depends(get_cosmos_service),
) -> dict:
    """
    Create a food order.

    - Assigns a unique **ORD-XXXXXXXX** id
    - Sets **orderDate** to the current UTC timestamp
    - Default status is **Pending**
    """
    return cosmos.create_order(payload.model_dump())


@router.get(
    "/",
    summary="List all orders",
    response_description="Array of order documents, newest first",
)
def get_all_orders(
    cosmos: CosmosService = Depends(get_cosmos_service),
) -> list:
    """Return every order across all customers, sorted by orderDate descending."""
    return cosmos.get_all_orders()


@router.get(
    "/{order_id}",
    summary="Get a single order with its items",
    response_description='{"order": {...}, "items": [...]}',
)
def get_order(
    order_id: str,
    cosmos: CosmosService = Depends(get_cosmos_service),
) -> dict:
    """
    Return the order document **plus** all child order items in one response.

    Example response shape:
    ```json
    {
      "order": { "id": "ORD-ABC12345", ... },
      "items": [ { "id": "ITEM-XYZ99", ... } ]
    }
    ```
    """
    result = cosmos.get_order_with_items(order_id)
    if result is None:
        raise _404(order_id)
    return result


@router.put(
    "/{order_id}",
    summary="Update an order",
    response_description="The updated order document",
)
def update_order(
    order_id: str,
    payload: OrderUpdate,
    cosmos: CosmosService = Depends(get_cosmos_service),
) -> dict:
    """
    Partial update — only fields included in the request body are changed.
    Fields omitted (or set to null) are left as-is.
    """
    # Strip None values so we only merge what the caller explicitly supplied
    fields = {k: v for k, v in payload.model_dump().items() if v is not None}
    updated = cosmos.update_order(order_id, fields)
    if updated is None:
        raise _404(order_id)
    return updated


@router.delete(
    "/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an order and all its items",
)
def delete_order(
    order_id: str,
    cosmos: CosmosService = Depends(get_cosmos_service),
) -> Response:
    """
    Delete the order document **and** cascade-delete every child order item.
    Returns 204 No Content on success.
    """
    if not cosmos.delete_order(order_id):
        raise _404(order_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
