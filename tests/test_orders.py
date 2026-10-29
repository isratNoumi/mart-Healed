import re
from datetime import timedelta

from sqlalchemy import text

from app.clock import utc_now
from conftest import HOUSTON_CENTRAL, HOUSTON_WEST, JOHN_ADDRESS, add_to_cart, card, card_number, pay, place_order


def inventory(db, product_id: int, store_id: int) -> int:
    db.expire_all()
    return db.execute(text("SELECT quantity FROM inventory WHERE product_id = :p AND store_id = :s"), {"p": product_id, "s": store_id}).scalar()


def attempt_count(db, order_id: int) -> int:
    return db.execute(
        text("SELECT COUNT(*) FROM payment_attempts pa JOIN payments p ON p.id = pa.payment_id WHERE p.order_id = :o"),
        {"o": order_id},
    ).scalar()


def cart_size(client) -> int:
    return client.get("/api/cart").json()["item_count"]


def new_order(client, **selection) -> dict:
    response = place_order(client, **selection)
    assert response.status_code == 201, response.text
    return response.json()


# ---------- scenarios from extended_plan.md ----------

def test_scenario_a_ship_to_home_success(john, db):
    order = new_order(john)
    assert order["status"] == "PENDING"
    assert re.fullmatch(r"BM-\d{8}-\d{5}", order["order_number"])

    response = pay(john, order["order_id"])
    assert response.status_code == 200, response.text
    result = response.json()
    assert (result["status"], result["payment_status"], result["fulfillment_status"]) == ("CONFIRMED", "PAID", "PROCESSING")
    assert inventory(db, 1, HOUSTON_CENTRAL) == 23
    assert cart_size(john) == 0

    detail = john.get(f"/api/orders/{order['order_id']}").json()
    assert detail["items"][0]["product_name"] == "DeWalt 20V MAX Cordless Drill Kit"
    assert detail["items"][0]["sku"] == "DW-DCD791D2-KIT"
    assert detail["total"] == 172.12
    assert detail["payment"]["card_display"] == "VISA •••• 4242"
    assert [event["status"] for event in detail["timeline"]] == ["CONFIRMED", "PROCESSING"]
    assert attempt_count(db, order["order_id"]) == 1


def test_scenario_b_declined_payment_keeps_cart(john, db):
    order = new_order(john)
    response = pay(john, order["order_id"], last4="0002")
    assert response.status_code == 402
    body = response.json()
    assert body["code"] == "CARD_DECLINED"
    assert (body["can_retry"], body["attempts_remaining"]) == (True, 4)

    assert cart_size(john) == 1
    assert inventory(db, 1, HOUSTON_CENTRAL) == 24
    detail = john.get(f"/api/orders/{order['order_id']}").json()
    assert (detail["status"], detail["payment_status"]) == ("PENDING", "DECLINED")
    assert detail["timeline"] == []


def test_scenario_c_retry_succeeds_and_records_two_attempts(john):
    order = new_order(john)
    assert pay(john, order["order_id"], last4="0341").status_code == 402
    response = pay(john, order["order_id"], last4="0341")
    assert response.status_code == 200

    payment = john.get(f"/api/payments/{response.json()['transaction_id']}").json()
    assert [(a["attempt_number"], a["status"]) for a in payment["attempts"]] == [(1, "DECLINED"), (2, "SUCCEEDED")]


def test_scenario_d_stock_drops_before_payment(john, db):
    order = new_order(john)
    db.execute(text("UPDATE inventory SET quantity = reserved_quantity WHERE product_id = 1 AND store_id = 1"))
    db.commit()

    response = pay(john, order["order_id"])
    assert response.status_code == 409
    assert response.json()["code"] == "INSUFFICIENT_INVENTORY"
    assert attempt_count(db, order["order_id"]) == 0
    assert cart_size(john) == 1
    assert john.get(f"/api/orders/{order['order_id']}").json()["status"] == "PENDING"


def test_scenario_e_timeout_then_retry(john, db):
    order = new_order(john)
    response = pay(john, order["order_id"], last4="0119")
    assert response.status_code == 402
    assert response.json()["code"] == "TIMEOUT"
    assert response.json()["transaction_id"] is None
    assert cart_size(john) == 1

    assert pay(john, order["order_id"]).status_code == 200
    statuses = db.execute(
        text("SELECT pa.status FROM payment_attempts pa JOIN payments p ON p.id = pa.payment_id WHERE p.order_id = :o ORDER BY pa.attempt_number"),
        {"o": order["order_id"]},
    ).scalars().all()
    assert statuses == ["TIMEOUT", "SUCCEEDED"]


def test_scenario_f_store_pickup(john, db):
    order = new_order(john, fulfillment_type="STORE_PICKUP", pickup_store_id=HOUSTON_WEST, shipping_address_id=None, billing_address_id=JOHN_ADDRESS)
    response = pay(john, order["order_id"])
    assert response.status_code == 200
    assert response.json()["fulfillment_status"] == "READY_FOR_PICKUP"
    assert inventory(db, 1, HOUSTON_WEST) == 6
    assert inventory(db, 1, HOUSTON_CENTRAL) == 24

    detail = john.get(f"/api/orders/{order['order_id']}").json()
    assert detail["fulfillment"]["store_name"] == "BuildMart Houston West"
    assert detail["shipping_cost"] == 0.0
    assert [event["status"] for event in detail["timeline"]] == ["CONFIRMED", "PROCESSING", "READY_FOR_PICKUP"]


# ---------- duplicate submissions ----------

def test_resubmitting_same_checkout_returns_same_draft(john):
    first = new_order(john)
    second = place_order(john)
    assert second.status_code == 200
    assert second.json()["order_id"] == first["order_id"]


def test_paying_a_confirmed_order_again_does_not_charge_twice(john, db):
    order = new_order(john)
    first = pay(john, order["order_id"]).json()
    second = pay(john, order["order_id"])
    assert second.status_code == 200
    assert second.json()["transaction_id"] == first["transaction_id"]
    assert attempt_count(db, order["order_id"]) == 1
    assert inventory(db, 1, HOUSTON_CENTRAL) == 23


# ---------- changes between placing and paying ----------

def test_cart_change_cancels_the_draft(john):
    order = new_order(john)
    add_to_cart(john, product_id=4)
    response = pay(john, order["order_id"])
    assert response.status_code == 409
    assert response.json()["code"] == "CART_CHANGED"
    assert john.get(f"/api/orders/{order['order_id']}").json()["status"] == "CANCELLED"


def test_price_change_before_payment_is_not_charged(john, db):
    order = new_order(john)
    db.execute(text("UPDATE regional_prices SET sale_price = 149 WHERE product_id = 1 AND region_id = 1"))
    db.commit()
    response = pay(john, order["order_id"])
    assert response.status_code == 409
    assert response.json()["code"] == "PRICE_CHANGED"
    assert attempt_count(db, order["order_id"]) == 0


def test_five_failed_attempts_cancel_the_order(john):
    order = new_order(john)
    for attempt in range(1, 6):
        body = pay(john, order["order_id"], last4="0002").json()
        assert body["attempt_number"] == attempt
    assert (body["can_retry"], body["attempts_remaining"]) == (False, 0)

    response = pay(john, order["order_id"])
    assert response.status_code == 409
    assert response.json()["code"] == "ORDER_CANCELLED"


def test_expired_draft_cannot_be_paid(john, db):
    order = new_order(john)
    db.execute(text("UPDATE orders SET created_at = :t WHERE id = :o"), {"t": f"{utc_now() - timedelta(minutes=31):%Y-%m-%d %H:%M:%S}", "o": order["order_id"]})
    db.commit()
    response = pay(john, order["order_id"])
    assert response.status_code == 409
    assert response.json()["code"] == "ORDER_EXPIRED"


# ---------- cards ----------

def test_pay_with_saved_card(john):
    order = new_order(john)
    response = john.post("/api/payments/process", json={"order_id": order["order_id"], "payment_method_id": 1})
    assert response.status_code == 200
    assert john.get(f"/api/orders/{order['order_id']}").json()["payment"]["card_display"] == "VISA •••• 4242"


def test_new_card_is_saved_only_when_requested_and_paid(john):
    order = new_order(john)
    assert pay(john, order["order_id"], last4="0002", save_card=True).status_code == 402
    assert len(john.get("/api/payment-methods").json()) == 2

    assert pay(john, order["order_id"], last4="4444", save_card=True).status_code == 200
    displays = [method["display"] for method in john.get("/api/payment-methods").json()]
    assert "VISA •••• 4444" in displays


def test_invalid_card_is_rejected_before_the_gateway(john, db):
    order = new_order(john)
    bad_number = "4000000000000001"
    response = john.post("/api/payments/process", json={"order_id": order["order_id"], "card": card(card_number=bad_number)})
    assert response.status_code == 422
    assert response.json()["code"] == "CARD_INVALID"
    assert "card_number" in response.json()["errors"]
    assert bad_number not in response.text
    assert attempt_count(db, order["order_id"]) == 0


def test_validation_errors_never_echo_card_details(john):
    number = card_number("4242")
    response = john.post("/api/payments/process", json={"order_id": 1, "card": card(expiry_month=13)})
    assert response.status_code == 422
    assert number not in response.text
    assert "123" not in response.text


def test_expired_card_is_rejected(john):
    order = new_order(john)
    response = john.post("/api/payments/process", json={"order_id": order["order_id"], "card": card(expiry_month=1, expiry_year=2020)})
    assert response.status_code == 422
    assert response.json()["errors"]["expiry"] == "This card has expired."


def test_card_validation_endpoint(john):
    valid = john.post("/api/payments/validate", json=card()).json()
    assert (valid["valid"], valid["brand"], valid["last4"]) == (True, "VISA", "4242")
    amex = john.post("/api/payments/validate", json=card(card_number="378282246310005", cvv="123")).json()
    assert amex["valid"] is False
    assert amex["errors"]["cvv"] == "Enter the 4-digit security code."


# ---------- history and access ----------

def test_order_history_lists_paid_orders_only(john):
    seeded = john.get("/api/orders").json()
    assert seeded["total"] == 1

    order = new_order(john)
    pay(john, order["order_id"], last4="0002")
    assert john.get("/api/orders").json()["total"] == 1

    pay(john, order["order_id"])
    history = john.get("/api/orders").json()
    assert history["total"] == 2
    assert history["items"][0]["order_id"] == order["order_id"]
    assert history["items"][0]["item_count"] == 1


def test_users_cannot_see_each_others_orders_or_payments(john, sarah):
    order = new_order(john)
    transaction_id = pay(john, order["order_id"]).json()["transaction_id"]

    assert sarah.get(f"/api/orders/{order['order_id']}").status_code == 404
    assert sarah.get(f"/api/payments/{transaction_id}").status_code == 404
    assert sarah.post("/api/payments/process", json={"order_id": order["order_id"], "card": card()}).status_code == 404
    assert sarah.post("/api/payments/process", json={"order_id": order["order_id"], "payment_method_id": 1}).status_code == 404
