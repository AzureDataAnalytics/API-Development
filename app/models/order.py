"""
app/models/order.py
-------------------
Pydantic models for the Order resource.

Three model layers:
  OrderCreate  – fields accepted on POST/PUT (no id, no orderDate)
  OrderUpdate  – all fields optional for PATCH-style PUT
  Order        – full document as stored in Cosmos DB
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

# Valid order lifecycle states
OrderStatus = Literal[
    "Pending",
    "Confirmed",
    "Preparing",
    "Out for Delivery",
    "Delivered",
    "Cancelled",
]


class DeliveryAddress(BaseModel):
    """Embedded sub-document for the delivery location."""

    street: str = Field(..., examples=["123 Main Street"])
    city: str = Field(..., examples=["Seattle"])
    state: str = Field(..., examples=["WA"])
    zipCode: str = Field(..., examples=["98101"])


class OrderCreate(BaseModel):
    """Payload expected when creating a new order."""

    customerId: str = Field(..., examples=["CUST-1001"])
    customerName: str = Field(..., examples=["John Smith"])
    customerEmail: str = Field(..., examples=["john.smith@email.com"])
    status: OrderStatus = "Pending"
    totalAmount: float = Field(..., gt=0, examples=[24.50])
    currency: str = Field(default="USD", examples=["USD"])
    deliveryAddress: DeliveryAddress


class OrderUpdate(BaseModel):
    """All fields optional — only supplied fields are merged into the document."""

    customerName: Optional[str] = None
    customerEmail: Optional[str] = None
    status: Optional[OrderStatus] = None
    totalAmount: Optional[float] = Field(default=None, gt=0)
    deliveryAddress: Optional[DeliveryAddress] = None


class Order(OrderCreate):
    """Full order document as it exists in Cosmos DB."""

    id: str
    orderDate: datetime

    model_config = {"from_attributes": True}
