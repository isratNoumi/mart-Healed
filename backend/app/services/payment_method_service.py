from sqlalchemy.orm import Session

from ..clock import utc_now
from ..models import PaymentMethod, User
from ..schemas import PaymentMethodRequest, PaymentMethodResponse
from .address_service import BILLING_TYPES, find_user_address
from .errors import ServiceError
from .payment_service import card_display, check_card, is_expired


def payment_method_response(method: PaymentMethod) -> PaymentMethodResponse:
    return PaymentMethodResponse(
        id=method.id,
        card_brand=method.card_brand,
        last4=method.last4,
        expiry_month=method.expiry_month,
        expiry_year=method.expiry_year,
        billing_address_id=method.billing_address_id,
        is_default=bool(method.is_default),
        is_expired=is_expired(method.expiry_month, method.expiry_year),
        display=card_display(method.card_brand, method.last4),
    )


def list_payment_methods(db: Session, user: User) -> list[PaymentMethod]:
    return (
        db.query(PaymentMethod)
        .filter(PaymentMethod.user_id == user.id)
        .order_by(PaymentMethod.is_default.desc(), PaymentMethod.id)
        .all()
    )


def find_user_payment_method(db: Session, user: User, method_id: int) -> PaymentMethod | None:
    return db.query(PaymentMethod).filter(PaymentMethod.id == method_id, PaymentMethod.user_id == user.id).first()


def save_card(
    db: Session,
    user: User,
    brand: str,
    last4: str,
    expiry_month: int,
    expiry_year: int,
    billing_address_id: int | None,
    make_default: bool,
) -> tuple[PaymentMethod, bool]:
    """Store only the brand, last 4 digits and expiry. Returns (method, created)."""
    existing = (
        db.query(PaymentMethod)
        .filter_by(user_id=user.id, card_brand=brand, last4=last4, expiry_month=expiry_month, expiry_year=expiry_year)
        .first()
    )
    if existing is not None:
        return existing, False
    make_default = make_default or not list_payment_methods(db, user)
    if make_default:
        db.query(PaymentMethod).filter(PaymentMethod.user_id == user.id, PaymentMethod.is_default == 1).update(
            {PaymentMethod.is_default: 0}, synchronize_session="fetch"
        )
        db.flush()
    method = PaymentMethod(
        user_id=user.id,
        type="card",
        card_brand=brand,
        last4=last4,
        expiry_month=expiry_month,
        expiry_year=expiry_year,
        billing_address_id=billing_address_id,
        is_default=1 if make_default else 0,
        created_at=utc_now(),
    )
    db.add(method)
    db.flush()
    return method, True


def create_payment_method(db: Session, user: User, data: PaymentMethodRequest) -> PaymentMethod:
    check = check_card(data.card_number.get_secret_value(), data.expiry_month, data.expiry_year, data.cvv.get_secret_value())
    if not check.valid:
        raise ServiceError(422, "CARD_INVALID", "Please correct the card details.", errors=check.errors)
    if data.billing_address_id is not None:
        address = find_user_address(db, user, data.billing_address_id)
        if address is None or address.type not in BILLING_TYPES:
            raise ServiceError(422, "BILLING_ADDRESS_INVALID", "Choose one of your billing addresses.")
    method, created = save_card(
        db, user, check.brand, check.last4, data.expiry_month, data.expiry_year, data.billing_address_id, data.is_default
    )
    if not created:
        raise ServiceError(409, "CARD_ALREADY_SAVED", "This card is already saved.")
    return method
