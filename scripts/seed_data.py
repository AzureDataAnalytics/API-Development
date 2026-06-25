"""
scripts/seed_data.py
--------------------
Loads 100 sample orders and ~350 order items into Cosmos DB.
Orders span 8 food categories with realistic prices, nutrition info,
customer names, addresses and order dates.

Usage:
    python scripts/seed_data.py            # upsert everything
    python scripts/seed_data.py --clear    # wipe existing data first, then seed
"""
from __future__ import annotations

import os
import random
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from azure.cosmos import CosmosClient
from dotenv import load_dotenv

from app.config import get_settings

load_dotenv()

# ── Menu catalogue ────────────────────────────────────────────────────────────
# Tuple layout: (name, price, calories, protein_g, carbs_g, fat_g, [allergies])

MENU: dict[str, list[tuple]] = {
    "pizza": [
        ("Margherita Pizza",       14.99, 285, 12, 36, 10, ["Gluten", "Milk"]),
        ("Pepperoni Pizza",        16.99, 320, 15, 36, 14, ["Gluten", "Milk"]),
        ("Veggie Supreme Pizza",   15.99, 260, 11, 34,  9, ["Gluten", "Milk"]),
        ("BBQ Chicken Pizza",      17.99, 350, 22, 38, 13, ["Gluten", "Milk"]),
        ("Four Cheese Pizza",      18.99, 380, 18, 35, 18, ["Gluten", "Milk"]),
        ("Hawaiian Pizza",         15.49, 295, 14, 37, 10, ["Gluten", "Milk"]),
    ],
    "burger": [
        ("Classic Beef Burger",    12.99, 650, 35, 45, 30, ["Gluten", "Milk", "Egg"]),
        ("Bacon Cheeseburger",     14.99, 780, 42, 45, 38, ["Gluten", "Milk", "Egg"]),
        ("Veggie Burger",          11.99, 480, 18, 52, 15, ["Gluten", "Soy"]),
        ("Mushroom Swiss Burger",  13.99, 620, 33, 44, 26, ["Gluten", "Milk"]),
        ("Double Smash Burger",    16.99, 920, 55, 46, 48, ["Gluten", "Milk", "Egg"]),
        ("Crispy Chicken Burger",  13.49, 680, 38, 50, 28, ["Gluten", "Milk"]),
    ],
    "salad": [
        ("Chicken Caesar Salad",   10.99, 450, 35, 20, 15, ["Milk", "Egg"]),
        ("Greek Salad",             9.99, 320,  8, 22, 18, ["Milk"]),
        ("Cobb Salad",             12.99, 580, 40, 18, 32, ["Milk", "Egg"]),
        ("Asian Sesame Salad",     11.99, 380, 22, 35, 14, ["Soy", "Sesame"]),
        ("Quinoa Power Bowl",      13.99, 520, 20, 65, 12, ["Soy"]),
        ("Caprese Salad",           9.49, 280, 14, 12, 18, ["Milk"]),
    ],
    "sandwich": [
        ("Turkey Club Sandwich",   10.99, 560, 38, 42, 18, ["Gluten", "Milk", "Egg"]),
        ("Grilled Chicken Wrap",    8.99, 520, 40, 32, 18, ["Gluten"]),
        ("Philly Cheesesteak",     13.99, 680, 42, 55, 22, ["Gluten", "Milk"]),
        ("BLT Sandwich",            9.99, 480, 22, 38, 20, ["Gluten", "Milk", "Egg"]),
        ("Italian Sub",            11.99, 620, 35, 48, 24, ["Gluten", "Milk"]),
        ("Tuna Melt",              10.49, 540, 30, 40, 22, ["Gluten", "Milk", "Fish"]),
    ],
    "sushi": [
        ("Salmon Nigiri (2pcs)",    8.99, 180, 14, 24,  4, ["Fish", "Soy"]),
        ("Spicy Tuna Roll",        12.99, 290, 18, 38,  8, ["Fish", "Soy", "Sesame"]),
        ("California Roll (8pcs)", 10.99, 260,  9, 38,  7, ["Crustaceans", "Soy"]),
        ("Dragon Roll",            15.99, 420, 22, 52, 12, ["Fish", "Crustaceans", "Soy"]),
        ("Miso Soup",               3.99,  45,  3,  5,  1, ["Soy"]),
        ("Edamame",                 4.99,  95,  8,  9,  4, ["Soy"]),
        ("Gyoza (5pcs)",            7.99, 220, 12, 28,  8, ["Gluten", "Soy"]),
    ],
    "mexican": [
        ("Beef Tacos (3pcs)",      10.99, 520, 28, 45, 22, ["Gluten", "Milk"]),
        ("Chicken Burrito",        12.99, 750, 48, 82, 18, ["Gluten", "Milk"]),
        ("Veggie Quesadilla",       9.99, 480, 16, 52, 20, ["Gluten", "Milk"]),
        ("Guacamole & Chips",       7.99, 380,  5, 42, 22, ["Gluten"]),
        ("Chicken Enchiladas",     13.99, 680, 42, 58, 24, ["Gluten", "Milk"]),
        ("Fish Tacos (2pcs)",      11.49, 440, 30, 42, 16, ["Gluten", "Fish"]),
        ("Nachos Supreme",          9.49, 620, 22, 70, 28, ["Gluten", "Milk"]),
    ],
    "indian": [
        ("Chicken Tikka Masala",   14.99, 480, 35, 28, 22, ["Milk"]),
        ("Lamb Biryani",           16.99, 620, 38, 72, 18, ["Milk"]),
        ("Palak Paneer",           12.99, 360, 18, 22, 20, ["Milk"]),
        ("Garlic Naan (2pcs)",      4.99, 280,  8, 48,  6, ["Gluten", "Milk"]),
        ("Mango Lassi",             4.99, 220,  6, 42,  4, ["Milk"]),
        ("Samosa (2pcs)",           5.99, 180,  4, 22,  8, ["Gluten"]),
        ("Dal Makhani",            11.99, 320, 14, 40, 12, ["Milk"]),
    ],
    "chinese": [
        ("Kung Pao Chicken",       13.99, 420, 32, 28, 18, ["Soy", "Peanuts"]),
        ("Beef & Broccoli",        14.99, 380, 28, 22, 16, ["Soy", "Gluten"]),
        ("Shrimp Fried Rice",      12.99, 520, 24, 68, 14, ["Crustaceans", "Soy", "Egg"]),
        ("Spring Rolls (4pcs)",     6.99, 220,  8, 28,  9, ["Gluten", "Soy"]),
        ("Hot & Sour Soup",         5.99, 120,  8, 14,  4, ["Soy", "Egg"]),
        ("Sweet & Sour Pork",      13.49, 460, 24, 48, 18, ["Gluten", "Soy"]),
        ("Dim Sum Basket (4pcs)",   8.99, 280, 14, 32, 10, ["Gluten", "Soy"]),
    ],
}

# ── Customer pool ─────────────────────────────────────────────────────────────

CUSTOMERS = [
    {"id": "CUST-1001", "name": "John Smith",       "email": "john.smith@email.com",       "street": "123 Main Street",         "city": "Seattle",       "state": "WA", "zip": "98101"},
    {"id": "CUST-1002", "name": "Jane Doe",          "email": "jane.doe@email.com",          "street": "456 Oak Avenue",          "city": "Portland",      "state": "OR", "zip": "97201"},
    {"id": "CUST-1003", "name": "Michael Johnson",   "email": "michael.j@email.com",         "street": "789 Elm Drive",           "city": "San Francisco", "state": "CA", "zip": "94102"},
    {"id": "CUST-1004", "name": "Sarah Williams",    "email": "s.williams@email.com",        "street": "321 Maple Lane",          "city": "Austin",        "state": "TX", "zip": "78701"},
    {"id": "CUST-1005", "name": "Robert Brown",      "email": "r.brown@email.com",           "street": "654 Pine Street",         "city": "Chicago",       "state": "IL", "zip": "60601"},
    {"id": "CUST-1006", "name": "Emily Davis",       "email": "emily.davis@email.com",       "street": "987 Cedar Court",         "city": "New York",      "state": "NY", "zip": "10001"},
    {"id": "CUST-1007", "name": "David Wilson",      "email": "d.wilson@email.com",          "street": "147 Birch Boulevard",     "city": "Denver",        "state": "CO", "zip": "80201"},
    {"id": "CUST-1008", "name": "Emma Taylor",       "email": "e.taylor@email.com",          "street": "258 Walnut Road",         "city": "Miami",         "state": "FL", "zip": "33101"},
    {"id": "CUST-1009", "name": "James Anderson",    "email": "james.a@email.com",           "street": "369 Spruce Way",          "city": "Phoenix",       "state": "AZ", "zip": "85001"},
    {"id": "CUST-1010", "name": "Olivia Martin",     "email": "olivia.m@email.com",          "street": "741 Poplar Place",        "city": "Dallas",        "state": "TX", "zip": "75201"},
    {"id": "CUST-1011", "name": "Christopher Lee",   "email": "c.lee@email.com",             "street": "852 Willow Court",        "city": "Boston",        "state": "MA", "zip": "02101"},
    {"id": "CUST-1012", "name": "Sophia Thompson",   "email": "sophia.t@email.com",          "street": "963 Hickory Terrace",     "city": "Atlanta",       "state": "GA", "zip": "30301"},
    {"id": "CUST-1013", "name": "Matthew Garcia",    "email": "m.garcia@email.com",          "street": "159 Aspen Circle",        "city": "Las Vegas",     "state": "NV", "zip": "89101"},
    {"id": "CUST-1014", "name": "Isabella Martinez", "email": "i.martinez@email.com",        "street": "357 Sycamore Lane",       "city": "Houston",       "state": "TX", "zip": "77001"},
    {"id": "CUST-1015", "name": "Daniel Rodriguez",  "email": "d.rodriguez@email.com",       "street": "468 Magnolia Drive",      "city": "San Diego",     "state": "CA", "zip": "92101"},
    {"id": "CUST-1016", "name": "Mia Hernandez",     "email": "mia.h@email.com",             "street": "579 Chestnut Street",     "city": "Philadelphia",  "state": "PA", "zip": "19101"},
    {"id": "CUST-1017", "name": "William Jackson",   "email": "w.jackson@email.com",         "street": "682 Dogwood Avenue",      "city": "Nashville",     "state": "TN", "zip": "37201"},
    {"id": "CUST-1018", "name": "Charlotte White",   "email": "c.white@email.com",           "street": "793 Hawthorn Court",      "city": "Minneapolis",   "state": "MN", "zip": "55401"},
    {"id": "CUST-1019", "name": "Benjamin Harris",   "email": "b.harris@email.com",          "street": "814 Ironwood Place",      "city": "Portland",      "state": "ME", "zip": "04101"},
    {"id": "CUST-1020", "name": "Amelia Clark",      "email": "amelia.c@email.com",          "street": "925 Juniper Road",        "city": "Tucson",        "state": "AZ", "zip": "85701"},
]

STATUSES = ["Pending", "Confirmed", "Preparing", "Out for Delivery", "Delivered", "Cancelled"]
# Historical data skews heavily toward Delivered
STATUS_WEIGHTS = [5, 10, 10, 10, 60, 5]

CATEGORIES = list(MENU.keys())  # 8 categories


def _random_date(days_back: int = 180) -> str:
    """Return a random ISO-8601 UTC timestamp within the last N days."""
    offset = timedelta(seconds=random.randint(0, days_back * 86400))
    return (datetime.now(timezone.utc) - offset).isoformat()


def build_records() -> tuple[list[dict], list[dict]]:
    """
    Build 100 order dicts and ~350 item dicts.
    Returns (orders, items) as plain dicts ready for Cosmos upsert.
    """
    orders: list[dict] = []
    items: list[dict] = []
    item_counter = 10001

    for order_num in range(100):
        order_id = f"ORD-{10001 + order_num}"
        customer = CUSTOMERS[order_num % len(CUSTOMERS)]

        # Round-robin through categories for variety, with slight randomness
        category = CATEGORIES[(order_num + random.randint(0, 2)) % len(CATEGORIES)]
        pool = MENU[category]

        # 2-5 distinct items per order
        num_items = random.randint(2, min(5, len(pool)))
        chosen = random.sample(pool, num_items)

        order_items: list[dict] = []
        for name, price, cal, prot, carbs, fat, allergies in chosen:
            qty = random.randint(1, 3)
            order_items.append({
                "id": f"ITEM-{item_counter}",
                "orderId": order_id,
                "itemName": name,
                "quantity": qty,
                "pricePerItem": price,
                "calories": cal,
                "protein": float(prot),
                "carbohydrates": float(carbs),
                "fat": float(fat),
                "allergies": allergies,
            })
            item_counter += 1

        total = round(sum(i["pricePerItem"] * i["quantity"] for i in order_items), 2)

        orders.append({
            "id": order_id,
            "customerId": customer["id"],
            "customerName": customer["name"],
            "customerEmail": customer["email"],
            "orderDate": _random_date(),
            "status": random.choices(STATUSES, STATUS_WEIGHTS)[0],
            "totalAmount": total,
            "currency": "USD",
            "deliveryAddress": {
                "street": customer["street"],
                "city": customer["city"],
                "state": customer["state"],
                "zipCode": customer["zip"],
            },
        })
        items.extend(order_items)

    return orders, items


def clear_containers(orders_ctr, items_ctr) -> None:
    """Delete all documents from both containers."""
    print("  Clearing orders...")
    for doc in orders_ctr.query_items(
        "SELECT c.id, c.customerId FROM c", enable_cross_partition_query=True
    ):
        orders_ctr.delete_item(item=doc["id"], partition_key=doc["customerId"])

    print("  Clearing order items...")
    for doc in items_ctr.query_items(
        "SELECT c.id, c.orderId FROM c", enable_cross_partition_query=True
    ):
        items_ctr.delete_item(item=doc["id"], partition_key=doc["orderId"])

    print("  Cleared.\n")


def seed(clear: bool = False) -> None:
    """Connect to Cosmos DB and load the sample data."""
    settings = get_settings()
    client = CosmosClient(url=settings.cosmos_endpoint, credential=settings.cosmos_key)
    db = client.get_database_client(settings.cosmos_database)
    orders_ctr = db.get_container_client(settings.orders_container)
    items_ctr = db.get_container_client(settings.order_items_container)

    if clear:
        print("Clearing existing data...")
        clear_containers(orders_ctr, items_ctr)

    orders, items = build_records()

    print(f"Inserting {len(orders)} orders...")
    for i, order in enumerate(orders, 1):
        orders_ctr.upsert_item(order)
        if i % 20 == 0:
            print(f"  {i}/{len(orders)} orders inserted")

    print(f"\nInserting {len(items)} order items...")
    for i, item in enumerate(items, 1):
        items_ctr.upsert_item(item)
        if i % 50 == 0:
            print(f"  {i}/{len(items)} items inserted")

    print(f"\nDone. Loaded {len(orders)} orders and {len(items)} order items.\n")


if __name__ == "__main__":
    seed(clear="--clear" in sys.argv)
