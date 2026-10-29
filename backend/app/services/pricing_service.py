from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from ..models import RegionalPrice

CENT = Decimal("0.01")
ZERO = Decimal("0.00")
# States without a BuildMart store are not taxed.
TAX_RATES = {
    "TX": Decimal("0.0825"),
    "GA": Decimal("0.089"),
    "AZ": Decimal("0.086"),
}


def money(value: float | int | str | Decimal) -> Decimal:
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def current_unit_price(db: Session, product_id: int, region_id: int) -> Decimal | None:
    price = db.query(RegionalPrice).filter_by(product_id=product_id, region_id=region_id).first()
    if price is None:
        return None
    return money(price.sale_price if price.sale_price is not None else price.price)


def tax_for(subtotal: Decimal, state: str | None) -> Decimal:
    return money(subtotal * TAX_RATES.get((state or "").upper(), ZERO))
