from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..clock import utc_now
from ..models import Address, Order, PaymentMethod, User
from ..schemas import AddressRequest, AddressResponse
from .errors import ServiceError

SHIPPING_TYPES = ("shipping", "both")
BILLING_TYPES = ("billing", "both")


def address_response(address: Address) -> AddressResponse:
    return AddressResponse(
        id=address.id,
        type=address.type,
        first_name=address.first_name,
        last_name=address.last_name,
        address_line1=address.address_line1,
        address_line2=address.address_line2,
        city=address.city,
        state=address.state,
        zip_code=address.zip_code,
        phone=address.phone,
        is_default=bool(address.is_default),
    )


def list_addresses(db: Session, user: User) -> list[Address]:
    return (
        db.query(Address)
        .filter(Address.user_id == user.id, Address.deleted_at.is_(None))
        .order_by(Address.is_default.desc(), Address.id)
        .all()
    )


def find_user_address(db: Session, user: User, address_id: int) -> Address | None:
    return (
        db.query(Address)
        .filter(Address.id == address_id, Address.user_id == user.id, Address.deleted_at.is_(None))
        .first()
    )


def get_user_address(db: Session, user: User, address_id: int) -> Address:
    address = find_user_address(db, user, address_id)
    if address is None:
        raise ServiceError(404, "ADDRESS_NOT_FOUND", "Address not found.")
    return address


def _clear_default(db: Session, user: User, keep_id: int | None = None) -> None:
    query = db.query(Address).filter(Address.user_id == user.id, Address.is_default == 1)
    if keep_id is not None:
        query = query.filter(Address.id != keep_id)
    query.update({Address.is_default: 0}, synchronize_session="fetch")
    db.flush()


def _apply(address: Address, data: AddressRequest) -> None:
    address.type = data.type
    address.first_name = data.first_name
    address.last_name = data.last_name
    address.address_line1 = data.address_line1
    address.address_line2 = data.address_line2
    address.city = data.city
    address.state = data.state
    address.zip_code = data.zip_code
    address.phone = data.phone


def _new_address(db: Session, user: User, data: AddressRequest, make_default: bool) -> Address:
    now = utc_now()
    address = Address(user_id=user.id, is_default=1 if make_default else 0, created_at=now, updated_at=now, deleted_at=None)
    _apply(address, data)
    db.add(address)
    db.flush()
    return address


def _used_by_orders(db: Session, address_id: int) -> bool:
    return (
        db.query(Order.id)
        .filter(or_(Order.shipping_address_id == address_id, Order.billing_address_id == address_id))
        .first()
        is not None
    )


def create_address(db: Session, user: User, data: AddressRequest) -> Address:
    make_default = data.is_default or not list_addresses(db, user)
    if make_default:
        _clear_default(db, user)
    return _new_address(db, user, data, make_default)


def update_address(db: Session, user: User, address_id: int, data: AddressRequest) -> Address:
    address = get_user_address(db, user, address_id)
    # A user with addresses always keeps one default, so an edit can't unset it.
    make_default = data.is_default or bool(address.is_default)

    if not _used_by_orders(db, address.id):
        if make_default:
            _clear_default(db, user, keep_id=address.id)
        _apply(address, data)
        address.is_default = 1 if make_default else 0
        address.updated_at = utc_now()
        db.flush()
        return address

    # Past orders point at this row, so edits go to a new row and the old one is hidden.
    now = utc_now()
    address.deleted_at = now
    address.is_default = 0
    address.updated_at = now
    db.flush()
    if make_default:
        _clear_default(db, user)
    replacement = _new_address(db, user, data, make_default)
    db.query(PaymentMethod).filter(
        PaymentMethod.user_id == user.id, PaymentMethod.billing_address_id == address.id
    ).update({PaymentMethod.billing_address_id: replacement.id}, synchronize_session="fetch")
    return replacement


def delete_address(db: Session, user: User, address_id: int) -> None:
    address = get_user_address(db, user, address_id)
    was_default = bool(address.is_default)
    now = utc_now()
    address.deleted_at = now
    address.is_default = 0
    address.updated_at = now
    db.flush()
    if was_default:
        replacement = (
            db.query(Address)
            .filter(Address.user_id == user.id, Address.deleted_at.is_(None))
            .order_by(Address.created_at.desc(), Address.id.desc())
            .first()
        )
        if replacement is not None:
            replacement.is_default = 1
            db.flush()
