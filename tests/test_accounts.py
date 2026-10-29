import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from conftest import JOHN_ADDRESS, card

NEW_ADDRESS = {
    "first_name": "John",
    "last_name": "Carter",
    "address_line1": "900 Main Street",
    "city": "Houston",
    "state": "tx",
    "zip_code": "77002",
    "phone": "(713) 555-0111",
}


def defaults(client) -> list[int]:
    return [address["id"] for address in client.get("/api/addresses").json() if address["is_default"]]


def test_address_fields_are_validated(john):
    response = john.post("/api/addresses", json={**NEW_ADDRESS, "state": "XX", "zip_code": "123", "phone": "555"})
    assert response.status_code == 422
    fields = {error["loc"][-1] for error in response.json()["detail"]}
    assert fields == {"state", "zip_code", "phone"}


def test_address_input_is_normalized(john):
    address = john.post("/api/addresses", json=NEW_ADDRESS).json()
    assert (address["state"], address["phone"]) == ("TX", "713-555-0111")


def test_new_default_address_replaces_old_default(john):
    created = john.post("/api/addresses", json={**NEW_ADDRESS, "is_default": True}).json()
    assert defaults(john) == [created["id"]]


def test_editing_an_address_used_by_an_order_keeps_order_history(john):
    response = john.put(f"/api/addresses/{JOHN_ADDRESS}", json={**NEW_ADDRESS, "address_line1": "1 New Street"})
    assert response.status_code == 200
    replacement = response.json()
    assert replacement["id"] != JOHN_ADDRESS
    assert replacement["is_default"] is True
    assert JOHN_ADDRESS not in [address["id"] for address in john.get("/api/addresses").json()]

    seeded_order = john.get("/api/orders/1").json()
    assert seeded_order["shipping_address"]["address_line1"] == "1847 Westheimer Road"


def test_editing_an_unused_address_updates_it_in_place(john):
    created = john.post("/api/addresses", json=NEW_ADDRESS).json()
    updated = john.put(f"/api/addresses/{created['id']}", json={**NEW_ADDRESS, "city": "Katy"}).json()
    assert (updated["id"], updated["city"]) == (created["id"], "Katy")


def test_deleting_the_default_address_promotes_another(john):
    assert john.delete(f"/api/addresses/{JOHN_ADDRESS}").status_code == 204
    remaining = john.get("/api/addresses").json()
    assert [address["id"] for address in remaining] == [2]
    assert remaining[0]["is_default"] is True


def test_users_cannot_change_each_others_addresses(sarah):
    assert sarah.put(f"/api/addresses/{JOHN_ADDRESS}", json=NEW_ADDRESS).status_code == 404
    assert sarah.delete(f"/api/addresses/{JOHN_ADDRESS}").status_code == 404
    assert JOHN_ADDRESS not in [address["id"] for address in sarah.get("/api/addresses").json()]


def test_database_allows_only_one_default_address(db):
    with pytest.raises(IntegrityError):
        db.execute(text(
            "INSERT INTO addresses (user_id, type, first_name, last_name, address_line1, city, state, zip_code, is_default) "
            "VALUES (1, 'both', 'A', 'B', 'C', 'Houston', 'TX', '77002', 1)"
        ))
        db.commit()


def test_saved_card_stores_only_last_four_digits(john, db):
    response = john.post("/api/payment-methods", json={**card("4444"), "billing_address_id": JOHN_ADDRESS})
    assert response.status_code == 201
    assert response.json()["display"] == "VISA •••• 4444"

    row = db.execute(text("SELECT * FROM payment_methods WHERE id = :i"), {"i": response.json()["id"]}).mappings().one()
    stored = " ".join(str(value) for value in row.values())
    assert card("4444")["card_number"] not in stored
    assert "123" not in stored.split()

    assert john.post("/api/payment-methods", json=card("4444")).status_code == 409


def test_saving_an_expired_card_is_rejected(john):
    response = john.post("/api/payment-methods", json=card(expiry_year=2020))
    assert response.status_code == 422
    assert response.json()["code"] == "CARD_INVALID"


def test_saved_cards_are_private(sarah):
    assert [method["last4"] for method in sarah.get("/api/payment-methods").json()] == ["5555"]
