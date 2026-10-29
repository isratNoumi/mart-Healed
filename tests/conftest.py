import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import get_db
from app.init_db import initialize_database
from app.main import app
from app.services import auth_service
from app.services.payment_service import luhn_valid

PASSWORD = "TestPass123!"
JOHN = "john.carter@example.com"
SARAH = "sarah.miller@example.com"
HOUSTON_CENTRAL = 1
HOUSTON_WEST = 2
DALLAS_NORTH = 4
PHOENIX_CENTRAL = 5
JOHN_ADDRESS = 1
SARAH_ADDRESS = 3


def card_number(last4: str) -> str:
    """A checksum-valid Visa number ending in the given digits."""
    for digit in "0123456789":
        number = f"40000000000{digit}{last4}"
        if luhn_valid(number):
            return number
    raise AssertionError(f"No valid card number ends in {last4}")


def card(last4: str = "4242", **overrides) -> dict:
    return {
        "cardholder_name": "Test Buyer",
        "card_number": card_number(last4),
        "expiry_month": 12,
        "expiry_year": 2030,
        "cvv": "123",
        **overrides,
    }


def quote(client: TestClient, **selection) -> dict:
    response = client.post("/api/checkout/validate", json={"store_id": HOUSTON_CENTRAL, **selection})
    assert response.status_code == 200, response.text
    return response.json()


def place_order(client: TestClient, **selection):
    selection = {"store_id": HOUSTON_CENTRAL, "fulfillment_type": "SHIP_TO_HOME", "shipping_address_id": JOHN_ADDRESS, **selection}
    total = quote(client, **selection)["total"]
    return client.post("/api/orders", json={**selection, "expected_total": total})


def pay(client: TestClient, order_id: int, last4: str = "4242", **extra):
    return client.post("/api/payments/process", json={"order_id": order_id, "card": card(last4), **extra})


def add_to_cart(client: TestClient, product_id: int, quantity: int = 1, store_id: int = HOUSTON_CENTRAL, region_id: int = 1):
    response = client.post(
        "/api/cart/items",
        json={"product_id": product_id, "quantity": quantity, "region_id": region_id, "store_id": store_id},
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def session_factory(tmp_path):
    path = tmp_path / "test.db"
    initialize_database(path, PASSWORD)
    engine = create_engine(f"sqlite:///{path.as_posix()}", connect_args={"check_same_thread": False})
    yield sessionmaker(bind=engine, autoflush=False, autocommit=False)
    engine.dispose()


@pytest.fixture
def db(session_factory):
    session = session_factory()
    yield session
    session.close()


@pytest.fixture
def make_client(session_factory):
    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    auth_service.reset_rate_limits()
    clients = []

    def factory(email: str | None = None) -> TestClient:
        client = TestClient(app, base_url="https://testserver")
        clients.append(client)
        if email:
            response = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
            assert response.status_code == 200, response.text
        return client

    yield factory
    for client in clients:
        client.close()
    app.dependency_overrides.clear()


@pytest.fixture
def john(make_client):
    return make_client(JOHN)


@pytest.fixture
def sarah(make_client):
    return make_client(SARAH)
