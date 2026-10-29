from sqlalchemy import update
from sqlalchemy.orm import Session

from ..clock import utc_now
from ..models import Inventory


def available_quantity(db: Session, product_id: int, store_id: int) -> int:
    inventory = db.query(Inventory).filter_by(product_id=product_id, store_id=store_id).first()
    return max(inventory.quantity - inventory.reserved_quantity, 0) if inventory else 0


def decrement_inventory(db: Session, product_id: int, store_id: int, quantity: int) -> bool:
    """Reduce stock only if enough is available; returns False instead of going negative."""
    result = db.execute(
        update(Inventory)
        .where(
            Inventory.product_id == product_id,
            Inventory.store_id == store_id,
            Inventory.quantity - Inventory.reserved_quantity >= quantity,
        )
        .values(quantity=Inventory.quantity - quantity, updated_at=utc_now())
        .execution_options(synchronize_session="fetch")
    )
    return result.rowcount == 1
