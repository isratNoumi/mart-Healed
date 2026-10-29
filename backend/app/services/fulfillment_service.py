from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from ..clock import today
from ..models import Address, Region, Store
from ..schemas import FulfillmentOption, PickupStoreOption
from .inventory_service import available_quantity
from .location_service import zip_in_region
from .pricing_service import ZERO

LABELS = {
    "SHIP_TO_HOME": "Ship to Home",
    "STORE_PICKUP": "Store Pickup",
    "DELIVERY": "Local Delivery",
}
SHIP_TO_HOME_COST = Decimal("9.99")
FREE_SHIPPING_THRESHOLD = Decimal("99.00")
DELIVERY_COST = Decimal("79.00")
SHIP_TO_HOME_BUSINESS_DAYS = 5
DELIVERY_DAYS = 2


@dataclass(frozen=True)
class StockLine:
    product_id: int
    quantity: int


def add_business_days(start: date, days: int) -> date:
    current = start
    while days > 0:
        current += timedelta(days=1)
        if current.weekday() < 5:
            days -= 1
    return current


def estimated_date(fulfillment_type: str, on: date | None = None) -> date:
    start = on or today()
    if fulfillment_type == "SHIP_TO_HOME":
        return add_business_days(start, SHIP_TO_HOME_BUSINESS_DAYS)
    if fulfillment_type == "DELIVERY":
        return start + timedelta(days=DELIVERY_DAYS)
    return start


def shipping_cost(fulfillment_type: str | None, subtotal: Decimal) -> Decimal:
    if fulfillment_type == "SHIP_TO_HOME":
        return ZERO if subtotal >= FREE_SHIPPING_THRESHOLD else SHIP_TO_HOME_COST
    if fulfillment_type == "DELIVERY":
        return DELIVERY_COST
    return ZERO


def unavailable_products(db: Session, store_id: int, lines: list[StockLine]) -> list[int]:
    return [line.product_id for line in lines if available_quantity(db, line.product_id, store_id) < line.quantity]


def fulfillment_options(
    db: Session,
    selected_store: Store,
    region: Region,
    lines: list[StockLine],
    subtotal: Decimal,
    shipping_address: Address | None,
) -> list[FulfillmentOption]:
    if not lines:
        base_reason = "Your cart is empty."
    elif unavailable_products(db, selected_store.id, lines):
        base_reason = f"Some items aren't in stock at {selected_store.name}."
    else:
        base_reason = None

    delivery_reason = base_reason
    if delivery_reason is None and shipping_address is not None and not zip_in_region(shipping_address.zip_code, region):
        delivery_reason = f"Delivery is only available to addresses in the {region.name} area."

    pickup_stores = []
    for store in db.query(Store).filter(Store.region_id == region.id, Store.is_active == 1).order_by(Store.id).all():
        missing = unavailable_products(db, store.id, lines)
        pickup_stores.append(
            PickupStoreOption(
                store_id=store.id,
                name=store.name,
                address=store.address,
                city=store.city,
                state=store.state,
                zip_code=store.zip_code,
                all_items_available=bool(lines) and not missing,
                unavailable_product_ids=missing,
            )
        )
    if not lines:
        pickup_reason = "Your cart is empty."
    elif any(store.all_items_available for store in pickup_stores):
        pickup_reason = None
    else:
        pickup_reason = "No store in your area has every item in stock."

    def option(fulfillment_type: str, reason: str | None, **extra) -> FulfillmentOption:
        return FulfillmentOption(
            type=fulfillment_type,
            label=LABELS[fulfillment_type],
            available=reason is None,
            reason=reason,
            cost=float(shipping_cost(fulfillment_type, subtotal)),
            estimated_date=estimated_date(fulfillment_type),
            **extra,
        )

    return [
        option("SHIP_TO_HOME", base_reason),
        option("STORE_PICKUP", pickup_reason, pickup_stores=pickup_stores),
        option("DELIVERY", delivery_reason),
    ]
