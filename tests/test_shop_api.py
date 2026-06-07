"""Pytest test suite for Shop API using requests."""

from __future__ import annotations

import threading

import pytest
import requests

from shop_api import shop_api
from shop_api.shop_api import HTTPServer, ShopAPIHandler


@pytest.fixture(scope="session")
def base_url(tmp_path_factory):
    """Start API server once for the whole test session on a random free port."""
    test_dir = tmp_path_factory.mktemp("shop_api")
    shop_api.DB_FILE = str(test_dir / "shop_test.db")
    shop_api.init_database()

    server = HTTPServer(("127.0.0.1", 0), ShopAPIHandler)
    host, port = server.server_address
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    yield f"http://{host}:{port}"

    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


@pytest.fixture(autouse=True)
def clean_database():
    """Reset data between tests to keep tests independent."""
    with shop_api.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM order_items")
        cursor.execute("DELETE FROM orders")
        cursor.execute("DELETE FROM cart")
        cursor.execute("DELETE FROM products")


def create_product(base_url, **overrides):
    payload = {
        "name": "Laptop",
        "description": "High-performance laptop",
        "price": 999.99,
        "stock": 10,
    }
    payload.update(overrides)
    response = requests.post(f"{base_url}/api/products", json=payload, timeout=3)
    assert response.status_code == 201
    return response.json()["id"]


def test_create_and_get_product(base_url):
    response = requests.post(
        f"{base_url}/api/products",
        json={"name": "Mouse", "price": 29.99, "stock": 50},
        timeout=3,
    )
    assert response.status_code == 201
    product_id = response.json()["id"]

    get_response = requests.get(f"{base_url}/api/products/{product_id}", timeout=3)
    assert get_response.status_code == 200
    product = get_response.json()["product"]
    assert product["name"] == "Mouse"
    assert product["price"] == 29.99
    assert product["stock"] == 50


def test_create_product_missing_required_fields(base_url):
    response = requests.post(
        f"{base_url}/api/products", json={"description": "No name and price"}, timeout=3
    )
    assert response.status_code == 400
    assert "Missing required fields" in response.json()["error"]


def test_update_product(base_url):
    product_id = create_product(base_url)

    update = requests.put(
        f"{base_url}/api/products/{product_id}",
        json={"price": 899.99, "stock": 7},
        timeout=3,
    )
    assert update.status_code == 200

    fetched = requests.get(f"{base_url}/api/products/{product_id}", timeout=3)
    product = fetched.json()["product"]
    assert product["price"] == 899.99
    assert product["stock"] == 7


def test_delete_product(base_url):
    product_id = create_product(base_url)

    delete_response = requests.delete(
        f"{base_url}/api/products/{product_id}", timeout=3
    )
    assert delete_response.status_code == 200

    get_response = requests.get(f"{base_url}/api/products/{product_id}", timeout=3)
    assert get_response.status_code == 404


def test_list_products(base_url):
    create_product(base_url, name="Keyboard", price=49.99)
    create_product(base_url, name="Monitor", price=199.99)
    create_product(base_url, name="Mouse", price=29.99)
    create_product(base_url, name="Laptop", price=999.99)
    create_product(base_url, name="Headphones", price=89.99)
    create_product(base_url, name="Webcam", price=59.99)

    response = requests.get(f"{base_url}/api/products", timeout=3)
    assert response.status_code == 200
    products = response.json()["products"]
    assert len(products) == 6
    names = {p["name"] for p in products}
    assert "Keyboard" in names
    assert "Monitor" in names
    assert "Mouse" in names
    assert "Laptop" in names
    assert "Headphones" in names
    assert "Webcam" in names
