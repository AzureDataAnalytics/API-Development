"""
tests/test_orders.py
--------------------
Unit tests for Orders and Order Items routes.

Cosmos DB calls are mocked — no live Azure connection required.

Run:
    pytest tests/ -v
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.cosmos_service import get_cosmos_service

# ── Sample fixtures ───────────────────────────────────────────────────────────

SAMPLE_ORDER = {
    "id": "ORD-TEST0001",
    "customerId": "CUST-9999",
    "customerName": "Test User",
    "customerEmail": "test@example.com",
    "orderDate": "2026-01-01T12:00:00+00:00",
    "status": "Pending",
    "totalAmount": 29.99,
    "currency": "USD",
    "deliveryAddress": {
        "street": "1 Test Lane",
        "city": "Testville",
        "state": "CA",
        "zipCode": "90001",
    },
}

SAMPLE_ITEM = {
    "id": "ITEM-TEST0001",
    "orderId": "ORD-TEST0001",
    "itemName": "Test Burger",
    "quantity": 2,
    "pricePerItem": 12.99,
    "calories": 650,
    "protein": 35.0,
    "carbohydrates": 45.0,
    "fat": 30.0,
    "allergies": ["Gluten", "Milk"],
}

CREATE_ORDER_PAYLOAD = {
    "customerId": "CUST-9999",
    "customerName": "Test User",
    "customerEmail": "test@example.com",
    "totalAmount": 29.99,
    "deliveryAddress": {
        "street": "1 Test Lane",
        "city": "Testville",
        "state": "CA",
        "zipCode": "90001",
    },
}

CREATE_ITEM_PAYLOAD = {
    "itemName": "Test Burger",
    "quantity": 2,
    "pricePerItem": 12.99,
    "calories": 650,
    "protein": 35.0,
    "carbohydrates": 45.0,
    "fat": 30.0,
    "allergies": ["Gluten", "Milk"],
}


# ── Mock factory ──────────────────────────────────────────────────────────────

def _make_mock() -> MagicMock:
    """Return a fully configured CosmosService mock."""
    m = MagicMock()
    m.create_order.return_value = SAMPLE_ORDER
    m.get_all_orders.return_value = [SAMPLE_ORDER]
    m.get_order_with_items.return_value = {"order": SAMPLE_ORDER, "items": [SAMPLE_ITEM]}
    m.get_order.return_value = SAMPLE_ORDER
    m.update_order.return_value = {**SAMPLE_ORDER, "status": "Confirmed"}
    m.delete_order.return_value = True
    m.create_item.return_value = SAMPLE_ITEM
    m.get_items_for_order.return_value = [SAMPLE_ITEM]
    m.get_item.return_value = SAMPLE_ITEM
    m.update_item.return_value = {**SAMPLE_ITEM, "quantity": 3}
    m.delete_item.return_value = True
    return m


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_cosmos():
    """Override the DI factory for every test in this module."""
    mock = _make_mock()
    app.dependency_overrides[get_cosmos_service] = lambda: mock
    yield mock
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ── Order tests ───────────────────────────────────────────────────────────────

class TestCreateOrder:
    def test_returns_201(self, client):
        resp = client.post("/api/orders/", json=CREATE_ORDER_PAYLOAD)
        assert resp.status_code == 201

    def test_returns_order_id(self, client):
        resp = client.post("/api/orders/", json=CREATE_ORDER_PAYLOAD)
        assert resp.json()["id"] == "ORD-TEST0001"

    def test_missing_required_field_returns_422(self, client):
        payload = {k: v for k, v in CREATE_ORDER_PAYLOAD.items() if k != "customerId"}
        resp = client.post("/api/orders/", json=payload)
        assert resp.status_code == 422

    def test_invalid_total_amount_returns_422(self, client):
        resp = client.post("/api/orders/", json={**CREATE_ORDER_PAYLOAD, "totalAmount": -5})
        assert resp.status_code == 422


class TestGetAllOrders:
    def test_returns_200(self, client):
        resp = client.get("/api/orders/")
        assert resp.status_code == 200

    def test_returns_list(self, client):
        resp = client.get("/api/orders/")
        assert isinstance(resp.json(), list)
        assert len(resp.json()) == 1


class TestGetOrder:
    def test_returns_order_and_items(self, client):
        resp = client.get("/api/orders/ORD-TEST0001")
        assert resp.status_code == 200
        body = resp.json()
        assert "order" in body
        assert "items" in body
        assert body["order"]["id"] == "ORD-TEST0001"

    def test_not_found_returns_404(self, client, mock_cosmos):
        mock_cosmos.get_order_with_items.return_value = None
        resp = client.get("/api/orders/ORD-MISSING")
        assert resp.status_code == 404
        assert "message" in resp.json()["detail"]


class TestUpdateOrder:
    def test_returns_updated_document(self, client):
        resp = client.put("/api/orders/ORD-TEST0001", json={"status": "Confirmed"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "Confirmed"

    def test_not_found_returns_404(self, client, mock_cosmos):
        mock_cosmos.update_order.return_value = None
        resp = client.put("/api/orders/ORD-MISSING", json={"status": "Confirmed"})
        assert resp.status_code == 404

    def test_invalid_status_returns_422(self, client):
        resp = client.put("/api/orders/ORD-TEST0001", json={"status": "Teleported"})
        assert resp.status_code == 422


class TestDeleteOrder:
    def test_returns_204(self, client):
        resp = client.delete("/api/orders/ORD-TEST0001")
        assert resp.status_code == 204

    def test_not_found_returns_404(self, client, mock_cosmos):
        mock_cosmos.delete_order.return_value = False
        resp = client.delete("/api/orders/ORD-MISSING")
        assert resp.status_code == 404


# ── Item tests ────────────────────────────────────────────────────────────────

class TestCreateItem:
    def test_returns_201(self, client):
        resp = client.post("/api/orders/ORD-TEST0001/items/", json=CREATE_ITEM_PAYLOAD)
        assert resp.status_code == 201

    def test_returns_item_id(self, client):
        resp = client.post("/api/orders/ORD-TEST0001/items/", json=CREATE_ITEM_PAYLOAD)
        assert resp.json()["id"] == "ITEM-TEST0001"

    def test_order_not_found_returns_404(self, client, mock_cosmos):
        mock_cosmos.get_order.return_value = None
        resp = client.post("/api/orders/ORD-MISSING/items/", json=CREATE_ITEM_PAYLOAD)
        assert resp.status_code == 404

    def test_invalid_quantity_returns_422(self, client):
        resp = client.post(
            "/api/orders/ORD-TEST0001/items/",
            json={**CREATE_ITEM_PAYLOAD, "quantity": 0},
        )
        assert resp.status_code == 422


class TestGetItems:
    def test_returns_list(self, client):
        resp = client.get("/api/orders/ORD-TEST0001/items/")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_order_not_found_returns_404(self, client, mock_cosmos):
        mock_cosmos.get_order.return_value = None
        resp = client.get("/api/orders/ORD-MISSING/items/")
        assert resp.status_code == 404


class TestGetItem:
    def test_returns_item(self, client):
        resp = client.get("/api/orders/ORD-TEST0001/items/ITEM-TEST0001")
        assert resp.status_code == 200
        assert resp.json()["itemName"] == "Test Burger"

    def test_not_found_returns_404(self, client, mock_cosmos):
        mock_cosmos.get_item.return_value = None
        resp = client.get("/api/orders/ORD-TEST0001/items/ITEM-MISSING")
        assert resp.status_code == 404


class TestUpdateItem:
    def test_returns_updated_item(self, client):
        resp = client.put(
            "/api/orders/ORD-TEST0001/items/ITEM-TEST0001",
            json={"quantity": 3},
        )
        assert resp.status_code == 200
        assert resp.json()["quantity"] == 3

    def test_not_found_returns_404(self, client, mock_cosmos):
        mock_cosmos.update_item.return_value = None
        resp = client.put(
            "/api/orders/ORD-TEST0001/items/ITEM-MISSING",
            json={"quantity": 3},
        )
        assert resp.status_code == 404


class TestDeleteItem:
    def test_returns_204(self, client):
        resp = client.delete("/api/orders/ORD-TEST0001/items/ITEM-TEST0001")
        assert resp.status_code == 204

    def test_not_found_returns_404(self, client, mock_cosmos):
        mock_cosmos.delete_item.return_value = False
        resp = client.delete("/api/orders/ORD-TEST0001/items/ITEM-MISSING")
        assert resp.status_code == 404
