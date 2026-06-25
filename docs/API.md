# Food Orders API — Endpoint Reference

Base URL: `http://localhost:8000`  
Interactive docs: `http://localhost:8000/docs`

---

## Orders

### POST /api/orders — Create Order

Creates a new order. Assigns a unique `ORD-XXXXXXXX` id and sets `orderDate` to the current UTC time.

**Request**
```http
POST /api/orders/
Content-Type: application/json
```
```json
{
  "customerId": "CUST-1001",
  "customerName": "John Smith",
  "customerEmail": "john.smith@email.com",
  "status": "Pending",
  "totalAmount": 35.97,
  "currency": "USD",
  "deliveryAddress": {
    "street": "123 Main Street",
    "city": "Seattle",
    "state": "WA",
    "zipCode": "98101"
  }
}
```

**Response — 201 Created**
```json
{
  "id": "ORD-A1B2C3D4",
  "customerId": "CUST-1001",
  "customerName": "John Smith",
  "customerEmail": "john.smith@email.com",
  "orderDate": "2026-06-25T14:32:00.123456+00:00",
  "status": "Pending",
  "totalAmount": 35.97,
  "currency": "USD",
  "deliveryAddress": {
    "street": "123 Main Street",
    "city": "Seattle",
    "state": "WA",
    "zipCode": "98101"
  }
}
```

**Error Responses**

| Status | Reason |
|--------|--------|
| 422 | Missing required field or invalid value (e.g. `totalAmount <= 0`) |
| 500 | Cosmos DB connection failure |

---

### GET /api/orders — List All Orders

Returns all orders sorted by `orderDate` descending.

**Request**
```http
GET /api/orders/
```

**Response — 200 OK**
```json
[
  {
    "id": "ORD-10101",
    "customerId": "CUST-1001",
    "customerName": "John Smith",
    "orderDate": "2026-06-20T10:00:00+00:00",
    "status": "Delivered",
    "totalAmount": 42.50,
    ...
  }
]
```

---

### GET /api/orders/{orderId} — Get Order with Items

Returns the order document **and** all child items in a single response.

**Request**
```http
GET /api/orders/ORD-10101
```

**Response — 200 OK**
```json
{
  "order": {
    "id": "ORD-10101",
    "customerId": "CUST-1001",
    "customerName": "John Smith",
    "customerEmail": "john.smith@email.com",
    "orderDate": "2026-06-20T10:00:00+00:00",
    "status": "Delivered",
    "totalAmount": 42.50,
    "currency": "USD",
    "deliveryAddress": {
      "street": "123 Main Street",
      "city": "Seattle",
      "state": "WA",
      "zipCode": "98101"
    }
  },
  "items": [
    {
      "id": "ITEM-20101",
      "orderId": "ORD-10101",
      "itemName": "Pepperoni Pizza",
      "quantity": 2,
      "pricePerItem": 16.99,
      "calories": 320,
      "protein": 15,
      "carbohydrates": 36,
      "fat": 14,
      "allergies": ["Gluten", "Milk"]
    }
  ]
}
```

**Error Responses**

| Status | Reason |
|--------|--------|
| 404 | Order not found |

---

### PUT /api/orders/{orderId} — Update Order

Partial update — only fields present in the body are changed.

**Request**
```http
PUT /api/orders/ORD-10101
Content-Type: application/json
```
```json
{
  "status": "Confirmed",
  "totalAmount": 45.00
}
```

**Response — 200 OK**

Returns the full updated order document.

**Valid status values**

`Pending` | `Confirmed` | `Preparing` | `Out for Delivery` | `Delivered` | `Cancelled`

**Error Responses**

| Status | Reason |
|--------|--------|
| 404 | Order not found |
| 422 | Invalid field value (e.g. unknown status string) |

---

### DELETE /api/orders/{orderId} — Delete Order

Deletes the order **and** cascades-deletes all child items.

**Request**
```http
DELETE /api/orders/ORD-10101
```

**Response — 204 No Content**

No response body.

**Error Responses**

| Status | Reason |
|--------|--------|
| 404 | Order not found |

---

## Order Items

### POST /api/orders/{orderId}/items — Create Item

Adds a food item to an existing order.

**Request**
```http
POST /api/orders/ORD-10101/items/
Content-Type: application/json
```
```json
{
  "itemName": "Chicken Caesar Salad",
  "quantity": 1,
  "pricePerItem": 10.99,
  "calories": 450,
  "protein": 35,
  "carbohydrates": 20,
  "fat": 15,
  "allergies": ["Milk", "Egg"]
}
```

**Response — 201 Created**
```json
{
  "id": "ITEM-E5F6G7H8",
  "orderId": "ORD-10101",
  "itemName": "Chicken Caesar Salad",
  "quantity": 1,
  "pricePerItem": 10.99,
  "calories": 450,
  "protein": 35.0,
  "carbohydrates": 20.0,
  "fat": 15.0,
  "allergies": ["Milk", "Egg"]
}
```

**Error Responses**

| Status | Reason |
|--------|--------|
| 404 | Parent order not found |
| 422 | Invalid field value (e.g. `quantity <= 0`) |

---

### GET /api/orders/{orderId}/items — List Items

Returns all items for the given order.

**Request**
```http
GET /api/orders/ORD-10101/items/
```

**Response — 200 OK**
```json
[
  {
    "id": "ITEM-20101",
    "orderId": "ORD-10101",
    "itemName": "Pepperoni Pizza",
    "quantity": 2,
    ...
  }
]
```

**Error Responses**

| Status | Reason |
|--------|--------|
| 404 | Parent order not found |

---

### GET /api/orders/{orderId}/items/{itemId} — Get Item

**Request**
```http
GET /api/orders/ORD-10101/items/ITEM-20101
```

**Response — 200 OK**

Returns the single item document.

**Error Responses**

| Status | Reason |
|--------|--------|
| 404 | Item not found in this order |

---

### PUT /api/orders/{orderId}/items/{itemId} — Update Item

Partial update — only supplied fields are changed.

**Request**
```http
PUT /api/orders/ORD-10101/items/ITEM-20101
Content-Type: application/json
```
```json
{
  "quantity": 3,
  "pricePerItem": 14.99
}
```

**Response — 200 OK**

Returns the full updated item document.

**Error Responses**

| Status | Reason |
|--------|--------|
| 404 | Item not found in this order |
| 422 | Invalid field value |

---

### DELETE /api/orders/{orderId}/items/{itemId} — Delete Item

Deletes one item. Does not affect sibling items or the parent order.

**Request**
```http
DELETE /api/orders/ORD-10101/items/ITEM-20101
```

**Response — 204 No Content**

No response body.

**Error Responses**

| Status | Reason |
|--------|--------|
| 404 | Item not found in this order |

---

## Health Check

### GET /health

```http
GET /health
```

**Response — 200 OK**
```json
{ "status": "ok" }
```

---

## HTTP Status Code Summary

| Code | Meaning |
|------|---------|
| 200 | Success with body |
| 201 | Resource created |
| 204 | Success, no body (delete operations) |
| 404 | Resource not found |
| 422 | Validation error (request body invalid) |
| 500 | Unexpected server error |

---

## Error Response Shape

All error responses follow this structure:

```json
{
  "detail": {
    "message": "Order 'ORD-XXXXX' not found"
  }
}
```

Validation errors (422) use FastAPI's standard format:
```json
{
  "detail": [
    {
      "type": "greater_than",
      "loc": ["body", "totalAmount"],
      "msg": "Input should be greater than 0"
    }
  ]
}
```
