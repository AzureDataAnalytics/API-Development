"""
app/models/order_item.py
------------------------
Pydantic models for the OrderItem resource.

Three model layers:
  OrderItemCreate  – fields accepted when adding an item
  OrderItemUpdate  – all fields optional for partial updates
  OrderItem        – full document as stored in Cosmos DB
"""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class OrderItemCreate(BaseModel):
    """Payload expected when creating a new order item."""

    itemName: str = Field(..., examples=["Chicken Caesar Salad"])
    quantity: int = Field(..., gt=0, examples=[1])
    pricePerItem: float = Field(..., gt=0, examples=[10.99])
    calories: int = Field(..., ge=0, examples=[450])
    protein: float = Field(..., ge=0, examples=[35.0])
    carbohydrates: float = Field(..., ge=0, examples=[20.0])
    fat: float = Field(..., ge=0, examples=[15.0])
    allergies: List[str] = Field(default=[], examples=[["Milk", "Egg"]])
    # Set automatically by the image upload endpoint — not supplied by callers on create
    imageUrl: Optional[str] = Field(default=None, description="Public blob URL, set via the /image endpoints")


class ImageFileUpload(BaseModel):
    """Metadata returned after a successful image upload."""

    itemId: str
    imageUrl: str
    format: Literal["file", "base64"]


class ImageBase64Payload(BaseModel):
    """Request body for the base64 upload endpoint."""

    image_base64: str = Field(
        ...,
        description="Raw base64-encoded image bytes (no data-URI prefix needed)",
        examples=["iVBORw0KGgoAAAANSUhEUgAA..."],
    )
    filename: str = Field(
        ...,
        description="Original filename including extension (.jpg / .png)",
        examples=["pepperoni-pizza.jpg"],
    )


class OrderItemUpdate(BaseModel):
    """All fields optional — only supplied fields are merged into the document."""

    itemName: Optional[str] = None
    quantity: Optional[int] = Field(default=None, gt=0)
    pricePerItem: Optional[float] = Field(default=None, gt=0)
    calories: Optional[int] = Field(default=None, ge=0)
    protein: Optional[float] = Field(default=None, ge=0)
    carbohydrates: Optional[float] = Field(default=None, ge=0)
    fat: Optional[float] = Field(default=None, ge=0)
    allergies: Optional[List[str]] = None


class OrderItem(OrderItemCreate):
    """Full order item document as it exists in Cosmos DB."""

    id: str
    orderId: str

    model_config = {"from_attributes": True}
