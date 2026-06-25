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

## Item Images

Item images are stored in a **private** Azure Blob Storage container (`item-images`). Public internet access is disabled at both the storage account and container level — no blob URL is ever returned to callers. All image traffic is proxied through the API via the `GET /{itemId}/image` endpoint, which means access control stays in the application layer.

| Property | Value |
|----------|-------|
| Supported formats | JPEG, PNG (`.jpg` `.jpeg` `.png`) |
| Max file size | 8 MB |
| Cosmos `imageUrl` field | Internal blob path (e.g. `ITEM-20101/uuid-pizza.jpg`) — never a public URL |
| API serve path | `GET /api/orders/{orderId}/items/{itemId}/image` |
| Old image on replace | Automatically deleted before the new one is stored |

Two upload methods are available — multipart file upload (ideal from a browser or Postman) and base64 JSON (ideal from mobile apps or when the image is already encoded).

---

### GET /api/orders/{orderId}/items/{itemId}/image — Serve Image

Retrieve an item's image. The API downloads the blob from private storage and streams the bytes directly to the caller — no storage URL is ever exposed.

**Request**
```http
GET /api/orders/ORD-10101/items/ITEM-20101/image
```

**Response — 200 OK**

Raw image bytes with the correct `Content-Type` header (`image/jpeg` or `image/png`).

**curl example**
```bash
# Save to file
curl -o pizza.jpg "http://localhost:8000/api/orders/ORD-10101/items/ITEM-20101/image"

# Display inline (macOS)
curl -s "http://localhost:8000/api/orders/ORD-10101/items/ITEM-20101/image" | open -f -a Preview
```

**Error Responses**

| Status | Reason |
|--------|--------|
| 404 | Order or item not found |
| 404 | Item exists but has no image uploaded |
| 404 | Blob missing from storage (stale reference) |

---

### PUT /api/orders/{orderId}/items/{itemId}/image — Upload Image File

Upload a JPG or PNG image using **multipart/form-data**. The file field key must be `file`.

**Request**
```http
PUT /api/orders/ORD-10101/items/ITEM-20101/image
Content-Type: multipart/form-data; boundary=----boundary
```
```
------boundary
Content-Disposition: form-data; name="file"; filename="pepperoni-pizza.jpg"
Content-Type: image/jpeg

<binary image bytes>
------boundary--
```

**Response — 200 OK**

The `imageUrl` returned is the **API serve path**, not a storage URL. Use it with `GET` to retrieve the image.

```json
{
  "itemId": "ITEM-20101",
  "imageUrl": "/api/orders/ORD-10101/items/ITEM-20101/image",
  "format": "file"
}
```

**curl example**
```bash
curl -X PUT "http://localhost:8000/api/orders/ORD-10101/items/ITEM-20101/image" \
  -F "file=@/path/to/pepperoni-pizza.jpg"
```

**Python example**
```python
import requests

with open("pepperoni-pizza.jpg", "rb") as f:
    resp = requests.put(
        "http://localhost:8000/api/orders/ORD-10101/items/ITEM-20101/image",
        files={"file": ("pepperoni-pizza.jpg", f, "image/jpeg")},
    )
print(resp.json())
# {'itemId': 'ITEM-20101', 'imageUrl': 'https://...', 'format': 'file'}
```

**PowerShell example**
```powershell
$response = Invoke-RestMethod `
    -Uri "http://localhost:8000/api/orders/ORD-10101/items/ITEM-20101/image" `
    -Method PUT `
    -InFile "C:\Images\pepperoni-pizza.jpg" `
    -ContentType "image/jpeg"
$response.imageUrl
```

**Error Responses**

| Status | Reason |
|--------|--------|
| 400 | File type not JPEG or PNG |
| 400 | File exceeds 8 MB limit |
| 404 | Order or item not found |

---

### PUT /api/orders/{orderId}/items/{itemId}/image/base64 — Upload Base64 Image

Upload a JPG or PNG image encoded as a **base64 string** in a JSON body. Useful from mobile apps or when reading images from a database or API. A `data:image/...;base64,` data-URI prefix is accepted but not required.

**Request**
```http
PUT /api/orders/ORD-10101/items/ITEM-20101/image/base64
Content-Type: application/json
```
```json
{
  "image_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI6QAAAABJRU5ErkJggg==",
  "filename": "pizza-thumbnail.png"
}
```

**Response — 200 OK**
```json
{
  "itemId": "ITEM-20101",
  "imageUrl": "/api/orders/ORD-10101/items/ITEM-20101/image",
  "format": "base64"
}
```

**curl example**
```bash
# Encode file to base64 first
BASE64=$(base64 -i pepperoni-pizza.jpg)

curl -X PUT "http://localhost:8000/api/orders/ORD-10101/items/ITEM-20101/image/base64" \
  -H "Content-Type: application/json" \
  -d "{\"image_base64\": \"$BASE64\", \"filename\": \"pepperoni-pizza.jpg\"}"
```

**Python example**
```python
import base64, requests

with open("pepperoni-pizza.jpg", "rb") as f:
    b64 = base64.b64encode(f.read()).decode()

resp = requests.put(
    "http://localhost:8000/api/orders/ORD-10101/items/ITEM-20101/image/base64",
    json={"image_base64": b64, "filename": "pepperoni-pizza.jpg"},
)
print(resp.json())
# {'itemId': 'ITEM-20101', 'imageUrl': 'https://...', 'format': 'base64'}
```

**PowerShell example**
```powershell
$bytes  = [System.IO.File]::ReadAllBytes("C:\Images\pepperoni-pizza.jpg")
$b64    = [Convert]::ToBase64String($bytes)
$body   = @{ image_base64 = $b64; filename = "pepperoni-pizza.jpg" } | ConvertTo-Json

$response = Invoke-RestMethod `
    -Uri "http://localhost:8000/api/orders/ORD-10101/items/ITEM-20101/image/base64" `
    -Method PUT `
    -Body $body `
    -ContentType "application/json"
$response.imageUrl
```

**Sending a data-URI from a browser `<canvas>`**
```javascript
// canvas.toDataURL() returns "data:image/png;base64,iVBORw0KGgo..."
// The API strips the prefix automatically — pass it as-is:
const dataUri = canvas.toDataURL("image/png");

await fetch(`/api/orders/${orderId}/items/${itemId}/image/base64`, {
  method: "PUT",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ image_base64: dataUri, filename: "capture.png" }),
});
```

**Error Responses**

| Status | Reason |
|--------|--------|
| 400 | Invalid base64 string |
| 400 | Decoded bytes are not a valid JPEG or PNG |
| 400 | Decoded image exceeds 8 MB |
| 400 | File extension not `.jpg`, `.jpeg`, or `.png` |
| 404 | Order or item not found |

---

### DELETE /api/orders/{orderId}/items/{itemId}/image — Remove Image

Removes the blob from Azure Blob Storage and sets `imageUrl` to `null` on the item document. Safe to call even when no image has been uploaded — returns 204 in both cases.

**Request**
```http
DELETE /api/orders/ORD-10101/items/ITEM-20101/image
```

**Response — 204 No Content**

No response body.

**curl example**
```bash
curl -X DELETE "http://localhost:8000/api/orders/ORD-10101/items/ITEM-20101/image"
```

**Python example**
```python
import requests

resp = requests.delete(
    "http://localhost:8000/api/orders/ORD-10101/items/ITEM-20101/image"
)
print(resp.status_code)  # 204
```

**Error Responses**

| Status | Reason |
|--------|--------|
| 404 | Order or item not found |

---

### Full Image Lifecycle — end-to-end example

```bash
# 1. Create an order
ORDER=$(curl -s -X POST http://localhost:8000/api/orders/ \
  -H "Content-Type: application/json" \
  -d '{"customerId":"CUST-99","customerName":"Alice","customerEmail":"alice@test.com",
       "status":"Pending","totalAmount":18.99,"currency":"USD",
       "deliveryAddress":{"street":"1 Pike Place","city":"Seattle","state":"WA","zipCode":"98101"}}')
ORDER_ID=$(echo $ORDER | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Order: $ORDER_ID"

# 2. Add a pizza item
ITEM=$(curl -s -X POST http://localhost:8000/api/orders/$ORDER_ID/items/ \
  -H "Content-Type: application/json" \
  -d '{"itemName":"Pepperoni Pizza","quantity":1,"pricePerItem":18.99,
       "calories":850,"protein":36,"carbohydrates":90,"fat":38,"allergies":["Gluten","Milk"]}')
ITEM_ID=$(echo $ITEM | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Item: $ITEM_ID"

# 3. Upload the image
UPLOAD=$(curl -s -X PUT http://localhost:8000/api/orders/$ORDER_ID/items/$ITEM_ID/image \
  -F "file=@/path/to/pepperoni-pizza.jpg")
echo "Image URL: $(echo $UPLOAD | python -c "import sys,json; print(json.load(sys.stdin)['imageUrl'])")"

# 4. Fetch the item — imageUrl is now populated
curl -s http://localhost:8000/api/orders/$ORDER_ID/items/$ITEM_ID | python -m json.tool

# 5. Remove the image
curl -s -X DELETE http://localhost:8000/api/orders/$ORDER_ID/items/$ITEM_ID/image
echo "Image removed (204)"
```

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
