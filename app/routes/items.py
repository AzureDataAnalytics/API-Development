"""
app/routes/items.py
-------------------
CRUD endpoints for Order Items, nested under /api/orders/{order_id}/items.

All handlers verify the parent order exists before touching items so that
callers get a meaningful 404 rather than an empty list.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status

from app.models.order_item import ImageBase64Payload, ImageFileUpload, OrderItemCreate, OrderItemUpdate
from app.services.blob_service import BlobService, get_blob_service
from app.services.cosmos_service import CosmosService, get_cosmos_service

_ALLOWED_MIME = {"image/jpeg", "image/png"}
_ALLOWED_EXT = {".jpg", ".jpeg", ".png"}

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


# ── Image endpoints ───────────────────────────────────────────────────────────
# Blob container is PRIVATE — no direct storage URL is ever returned to callers.
# Uploads store the internal blob path in Cosmos. The GET endpoint below proxies
# the bytes through the API so the only way to retrieve an image is via this API.


def _image_serve_path(order_id: str, item_id: str) -> str:
    return f"/api/orders/{order_id}/items/{item_id}/image"


@router.get(
    "/{item_id}/image",
    summary="Serve item image — proxied through the API",
    tags=["Item Images"],
)
def get_item_image(
    order_id: str,
    item_id: str,
    cosmos: CosmosService = Depends(get_cosmos_service),
    blob: BlobService = Depends(get_blob_service),
) -> Response:
    """
    Stream the item's image bytes directly through the API.

    The image is stored in a **private** Azure Blob Storage container and is
    never accessible via a direct storage URL. All image traffic passes through
    this endpoint so access control can be enforced at the application layer.

    Returns the raw image bytes with the correct `Content-Type` header
    (`image/jpeg` or `image/png`).
    """
    item = cosmos.get_item(order_id, item_id)
    if item is None:
        raise _item_404(order_id, item_id)

    blob_path = item.get("imageUrl")
    if not blob_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": f"Item '{item_id}' has no image"},
        )

    try:
        image_bytes, content_type = blob.download_image(blob_path)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Image blob not found in storage"},
        )

    return Response(content=image_bytes, media_type=content_type)


@router.put(
    "/{item_id}/image",
    summary="Upload item image — JPG or PNG file (multipart)",
    tags=["Item Images"],
)
async def upload_image_file(
    order_id: str,
    item_id: str,
    file: UploadFile = File(..., description="JPG or PNG image, max 8 MB"),
    cosmos: CosmosService = Depends(get_cosmos_service),
    blob: BlobService = Depends(get_blob_service),
) -> ImageFileUpload:
    """
    Upload a JPG or PNG image for this item via **multipart/form-data**.

    - Image is stored in a **private** blob container — no public URL is created
    - The returned `imageUrl` is the API path to retrieve the image:
      `/api/orders/{orderId}/items/{itemId}/image`
    - Replaces any previously stored image (old blob deleted automatically)

    **Postman tip:** Body → form-data → key `file` (type = File)
    """
    item = cosmos.get_item(order_id, item_id)
    if item is None:
        raise _item_404(order_id, item_id)

    if file.content_type not in _ALLOWED_MIME:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": f"Unsupported file type '{file.content_type}'. Use image/jpeg or image/png."},
        )

    file_bytes = await file.read()

    if item.get("imageUrl"):
        blob.delete_image(item["imageUrl"])

    try:
        blob_path = blob.upload_file(item_id, file_bytes, file.filename or "image.jpg")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"message": str(exc)})

    cosmos.update_item(order_id, item_id, {"imageUrl": blob_path})
    return ImageFileUpload(itemId=item_id, imageUrl=_image_serve_path(order_id, item_id), format="file")


@router.put(
    "/{item_id}/image/base64",
    summary="Upload item image — base64-encoded JSON body",
    tags=["Item Images"],
)
def upload_image_base64(
    order_id: str,
    item_id: str,
    payload: ImageBase64Payload,
    cosmos: CosmosService = Depends(get_cosmos_service),
    blob: BlobService = Depends(get_blob_service),
) -> ImageFileUpload:
    """
    Upload a JPG or PNG image encoded as a **base64 string** in a JSON body.

    ```json
    {
      "image_base64": "<base64 string>",
      "filename": "pepperoni-pizza.jpg"
    }
    ```

    A `data:image/...;base64,` prefix is accepted but not required.
    Image is stored privately; the returned `imageUrl` is the API serve path.
    """
    item = cosmos.get_item(order_id, item_id)
    if item is None:
        raise _item_404(order_id, item_id)

    if item.get("imageUrl"):
        blob.delete_image(item["imageUrl"])

    try:
        blob_path = blob.upload_base64(item_id, payload.image_base64, payload.filename)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"message": str(exc)})

    cosmos.update_item(order_id, item_id, {"imageUrl": blob_path})
    return ImageFileUpload(itemId=item_id, imageUrl=_image_serve_path(order_id, item_id), format="base64")


@router.delete(
    "/{item_id}/image",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove an item's image",
    tags=["Item Images"],
)
def delete_item_image(
    order_id: str,
    item_id: str,
    cosmos: CosmosService = Depends(get_cosmos_service),
    blob: BlobService = Depends(get_blob_service),
) -> Response:
    """
    Delete the image blob from storage and clear `imageUrl` on the item document.
    Returns 204 No Content. Safe to call even if no image is set.
    """
    item = cosmos.get_item(order_id, item_id)
    if item is None:
        raise _item_404(order_id, item_id)

    if item.get("imageUrl"):
        blob.delete_image(item["imageUrl"])
        cosmos.update_item(order_id, item_id, {"imageUrl": None})

    return Response(status_code=status.HTTP_204_NO_CONTENT)
