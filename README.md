# Food Orders API

A production-quality REST API for managing food orders, built with **FastAPI** and **Azure Cosmos DB**.

## Architecture

```
Client (Postman / Browser)
         │
         ▼
  FastAPI Application
  ┌──────────────────────────────┐
  │  /api/orders  (orders.py)    │
  │  /api/orders/{id}/items      │
  │         │                    │
  │  CosmosService (singleton)   │
  └──────────┬───────────────────┘
             │
    Azure Cosmos DB (SQL API)
    ┌────────────────────────────┐
    │  Database: FoodOrdersDB    │
    │  ├─ orders   (/customerId) │
    │  └─ orderitems  (/orderId) │
    └────────────────────────────┘
```

**Design decisions**
- `orders` partitioned by `/customerId` — efficient per-customer reads
- `orderitems` partitioned by `/orderId` — all items for one order in a single partition, very low RU cost
- Cross-partition query only needed on `orders` when fetching by `orderId` alone
- Module-level `CosmosClient` singleton — not rebuilt per request
- Sync route handlers — FastAPI runs them in a thread pool; correct choice for the sync `azure-cosmos` SDK

---

## Project Structure

```
food-orders-api/
├── app/
│   ├── main.py                  ← FastAPI app, router registration
│   ├── config.py                ← Pydantic Settings (reads .env)
│   ├── models/
│   │   ├── order.py             ← OrderCreate / OrderUpdate / Order
│   │   └── order_item.py        ← OrderItemCreate / OrderItemUpdate / OrderItem
│   ├── routes/
│   │   ├── orders.py            ← POST/GET/PUT/DELETE /api/orders
│   │   └── items.py             ← POST/GET/PUT/DELETE /api/orders/{id}/items
│   └── services/
│       └── cosmos_service.py    ← All Cosmos DB reads/writes
│
├── scripts/
│   ├── create_database.py       ← Idempotent DB + container setup
│   └── seed_data.py             ← 100 orders, ~350 items across 8 cuisines
│
├── tests/
│   └── test_orders.py           ← Unit tests (mocked Cosmos)
│
├── docs/
│   └── API.md                   ← Endpoint reference
│
├── postman/
│   └── FoodOrders.postman_collection.json
│
├── requirements.txt
└── .env.example
```

---

## Setup

### 1. Clone and install

```bash
cd food-orders-api
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your Cosmos DB endpoint and key
```

```env
COSMOS_ENDPOINT=https://your-account.documents.azure.com:443/
COSMOS_KEY=your-primary-key
COSMOS_DATABASE=FoodOrdersDB
```

Find these values in **Azure Portal → Cosmos DB account → Keys**.

### 3. Create the database and containers

```bash
python scripts/create_database.py
```

Output:
```
Connecting to: https://your-account.documents.azure.com:443/
  [+] Created database: FoodOrdersDB
  [+] Created container 'orders'     (partition: /customerId)
  [+] Created container 'orderitems' (partition: /orderId)

Infrastructure ready.
```

### 4. Load sample data

```bash
python scripts/seed_data.py
```

Loads 100 orders and ~350 items across pizza, burger, salad, sandwich, sushi, Mexican, Indian, and Chinese cuisines.

To wipe existing data and re-seed:
```bash
python scripts/seed_data.py --clear
```

### 5. Start the API

```bash
uvicorn app.main:app --reload
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness check |
| POST | `/api/orders/` | Create order |
| GET | `/api/orders/` | List all orders |
| GET | `/api/orders/{orderId}` | Get order + items |
| PUT | `/api/orders/{orderId}` | Update order |
| DELETE | `/api/orders/{orderId}` | Delete order + items |
| POST | `/api/orders/{orderId}/items/` | Add item to order |
| GET | `/api/orders/{orderId}/items/` | List items for order |
| GET | `/api/orders/{orderId}/items/{itemId}` | Get single item |
| PUT | `/api/orders/{orderId}/items/{itemId}` | Update item |
| DELETE | `/api/orders/{orderId}/items/{itemId}` | Delete item |

Full documentation: [docs/API.md](docs/API.md)

---

## Interactive Docs

| URL | Description |
|-----|-------------|
| `http://localhost:8000/docs` | Swagger UI (try all endpoints live) |
| `http://localhost:8000/redoc` | ReDoc (clean reading view) |

---

## Running Tests

No live Azure connection needed — Cosmos DB is fully mocked.

```bash
pytest tests/ -v
```

Expected output:
```
tests/test_orders.py::TestCreateOrder::test_returns_201           PASSED
tests/test_orders.py::TestCreateOrder::test_returns_order_id      PASSED
tests/test_orders.py::TestGetAllOrders::test_returns_200          PASSED
...
23 passed in 0.45s
```

---

## Sample Requests

### Create an order

```bash
curl -X POST http://localhost:8000/api/orders/ \
  -H "Content-Type: application/json" \
  -d '{
    "customerId": "CUST-1001",
    "customerName": "John Smith",
    "customerEmail": "john.smith@email.com",
    "totalAmount": 35.97,
    "deliveryAddress": {
      "street": "123 Main Street",
      "city": "Seattle",
      "state": "WA",
      "zipCode": "98101"
    }
  }'
```

### Get an order with all items

```bash
curl http://localhost:8000/api/orders/ORD-10001
```

### Add an item to an order

```bash
curl -X POST http://localhost:8000/api/orders/ORD-10001/items/ \
  -H "Content-Type: application/json" \
  -d '{
    "itemName": "Chicken Caesar Salad",
    "quantity": 1,
    "pricePerItem": 10.99,
    "calories": 450,
    "protein": 35,
    "carbohydrates": 20,
    "fat": 15,
    "allergies": ["Milk", "Egg"]
  }'
```

### Update order status

```bash
curl -X PUT http://localhost:8000/api/orders/ORD-10001 \
  -H "Content-Type: application/json" \
  -d '{"status": "Confirmed"}'
```

### Delete an order (cascades to items)

```bash
curl -X DELETE http://localhost:8000/api/orders/ORD-10001
```

---

## Postman Collection

Import [postman/FoodOrders.postman_collection.json](postman/FoodOrders.postman_collection.json) into Postman.

The collection uses three variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `baseUrl` | `http://localhost:8000` | API base URL |
| `orderId` | _(empty)_ | Auto-populated by Create Order test script |
| `itemId` | _(empty)_ | Auto-populated by Create Item test script |

Run requests in order: **Create Order → Get Order → Create Item → ...** and the id variables will be set automatically.

---

## Order Status Lifecycle

```
Pending → Confirmed → Preparing → Out for Delivery → Delivered
                                                    ↘ Cancelled
```

---

## Seed Data Categories

| Category | Items |
|----------|-------|
| Pizza | Margherita, Pepperoni, Veggie Supreme, BBQ Chicken, Four Cheese, Hawaiian |
| Burger | Classic Beef, Bacon Cheese, Veggie, Mushroom Swiss, Double Smash, Crispy Chicken |
| Salad | Caesar, Greek, Cobb, Asian Sesame, Quinoa Power Bowl, Caprese |
| Sandwich | Turkey Club, Grilled Chicken Wrap, Philly Cheesesteak, BLT, Italian Sub, Tuna Melt |
| Sushi | Salmon Nigiri, Spicy Tuna Roll, California Roll, Dragon Roll, Miso Soup, Edamame, Gyoza |
| Mexican | Beef Tacos, Chicken Burrito, Veggie Quesadilla, Guacamole & Chips, Enchiladas, Fish Tacos, Nachos |
| Indian | Chicken Tikka Masala, Lamb Biryani, Palak Paneer, Garlic Naan, Mango Lassi, Samosa, Dal Makhani |
| Chinese | Kung Pao Chicken, Beef & Broccoli, Shrimp Fried Rice, Spring Rolls, Hot & Sour Soup, Sweet & Sour Pork, Dim Sum |
