from sqlalchemy import text

from conftest import (
    DALLAS_NORTH,
    HOUSTON_CENTRAL,
    HOUSTON_WEST,
    JOHN_ADDRESS,
    PHOENIX_CENTRAL,
    SARAH_ADDRESS,
    add_to_cart,
    place_order,
    quote,
)


def blocking_codes(result: dict) -> set[str]:
    return {issue["code"] for issue in result["issues"] if issue["blocking"]}


def test_checkout_requires_sign_in(make_client):
    anonymous = make_client()
    assert anonymous.get(f"/api/checkout?store_id={HOUSTON_CENTRAL}").status_code == 401
    assert anonymous.post("/api/orders", json={"store_id": 1, "fulfillment_type": "SHIP_TO_HOME", "expected_total": 1}).status_code == 401


def test_ship_to_home_quote_uses_server_prices_and_free_shipping(john):
    result = quote(john, fulfillment_type="SHIP_TO_HOME", shipping_address_id=JOHN_ADDRESS)
    assert result["subtotal"] == 159.00
    assert result["shipping_cost"] == 0.00  # free over $99
    assert result["tax"] == 13.12  # TX 8.25%
    assert result["total"] == 172.12
    assert result["can_place_order"] is True
    assert result["estimated_date"] is not None


def test_small_order_pays_shipping_and_destination_state_tax(sarah):
    add_to_cart(sarah, product_id=4)
    result = quote(sarah, fulfillment_type="SHIP_TO_HOME", shipping_address_id=SARAH_ADDRESS)
    assert result["subtotal"] == 19.97
    assert result["shipping_cost"] == 9.99
    assert result["tax"] == 1.78  # GA 8.9%
    assert result["total"] == 31.74


def test_checkout_page_preselects_default_address(john):
    response = john.get(f"/api/checkout?store_id={HOUSTON_CENTRAL}")
    assert response.status_code == 200
    body = response.json()
    assert body["quote"]["shipping_address_id"] == JOHN_ADDRESS
    assert [m["display"] for m in body["payment_methods"]] == ["VISA •••• 4242", "MASTERCARD •••• 1111"]
    assert {option["type"] for option in body["fulfillment_options"]} == {"SHIP_TO_HOME", "STORE_PICKUP", "DELIVERY"}


def test_pickup_options_flag_stores_without_enough_stock(john):
    add_to_cart(john, product_id=13, quantity=2)  # workbench: 3 at Houston Central, 1 at Houston West
    options = john.get(f"/api/fulfillment/options?store_id={HOUSTON_CENTRAL}").json()
    pickup = next(option for option in options if option["type"] == "STORE_PICKUP")
    stores = {store["store_id"]: store for store in pickup["pickup_stores"]}
    assert stores[HOUSTON_CENTRAL]["all_items_available"] is True
    assert stores[HOUSTON_WEST]["all_items_available"] is False
    assert stores[HOUSTON_WEST]["unavailable_product_ids"] == [13]

    result = quote(john, fulfillment_type="STORE_PICKUP", pickup_store_id=HOUSTON_WEST, billing_address_id=JOHN_ADDRESS)
    assert "INSUFFICIENT_INVENTORY" in blocking_codes(result)


def test_pickup_store_outside_region_is_rejected(john):
    result = quote(john, fulfillment_type="STORE_PICKUP", pickup_store_id=DALLAS_NORTH, billing_address_id=JOHN_ADDRESS)
    assert "PICKUP_STORE_INVALID" in blocking_codes(result)


def test_delivery_outside_store_area_is_rejected(john):
    phoenix = john.post("/api/addresses", json={
        "first_name": "John", "last_name": "Carter", "address_line1": "1 Camelback Rd",
        "city": "Phoenix", "state": "AZ", "zip_code": "85016", "phone": "602-555-0100",
    }).json()
    result = quote(john, fulfillment_type="DELIVERY", shipping_address_id=phoenix["id"])
    assert "DELIVERY_OUT_OF_AREA" in blocking_codes(result)

    options = john.get(f"/api/fulfillment/options?store_id={HOUSTON_CENTRAL}&shipping_address_id={phoenix['id']}").json()
    delivery = next(option for option in options if option["type"] == "DELIVERY")
    assert delivery["available"] is False


def test_missing_selections_are_reported(john):
    result = quote(john)
    assert "FULFILLMENT_REQUIRED" in blocking_codes(result)
    assert result["can_place_order"] is False


def test_empty_cart_cannot_place_order(sarah):
    response = place_order(sarah, shipping_address_id=SARAH_ADDRESS)
    assert response.status_code == 400
    assert response.json()["code"] == "EMPTY_CART"


def test_changed_total_is_rejected(john):
    response = john.post("/api/orders", json={
        "store_id": HOUSTON_CENTRAL, "fulfillment_type": "SHIP_TO_HOME", "shipping_address_id": JOHN_ADDRESS, "expected_total": 1.00,
    })
    assert response.status_code == 409
    assert response.json()["code"] == "TOTAL_CHANGED"
    assert response.json()["total"] == 172.12


def test_insufficient_stock_blocks_order(john, db):
    db.execute(text("UPDATE inventory SET quantity = reserved_quantity WHERE product_id = 1 AND store_id = 1"))
    db.commit()
    result = quote(john, fulfillment_type="SHIP_TO_HOME", shipping_address_id=JOHN_ADDRESS)
    assert "INSUFFICIENT_INVENTORY" in blocking_codes(result)
    response = place_order(john)
    assert response.status_code == 409
    assert response.json()["code"] == "CHECKOUT_INVALID"


def test_stale_cart_price_is_reported_but_not_blocking(john, db):
    db.execute(text("UPDATE cart_items SET unit_price = 150 WHERE cart_id = 1"))
    db.commit()
    result = quote(john, fulfillment_type="SHIP_TO_HOME", shipping_address_id=JOHN_ADDRESS)
    assert result["subtotal"] == 159.00
    assert any(issue["code"] == "PRICE_CHANGED" and not issue["blocking"] for issue in result["issues"])


def test_cart_location_without_stock_does_not_crash(john):
    add_to_cart(john, product_id=13)
    response = john.get(f"/api/cart?region_id=4&store_id={PHOENIX_CENTRAL}")
    assert response.status_code == 200
    workbench = next(item for item in response.json()["items"] if item["product_id"] == 13)
    assert workbench["quantity"] == 1
