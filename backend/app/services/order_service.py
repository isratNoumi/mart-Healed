import secrets
from collections import Counter
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import func, update
from sqlalchemy.orm import Session

from ..clock import utc_now
from ..models import (
    Address,
    CartItem,
    Fulfillment,
    Order,
    OrderItem,
    OrderStatusHistory,
    Payment,
    PaymentAttempt,
    Product,
    Store,
    User,
)
from ..schemas import (
    OrderDetailResponse,
    OrderFulfillmentResponse,
    OrderItemResponse,
    OrderListResponse,
    OrderPaymentResponse,
    OrderStatusEvent,
    OrderSummaryResponse,
    PaymentAttemptResponse,
    PaymentDetailResponse,
    PaymentResult,
    PendingOrderResponse,
    PlaceOrderRequest,
    ProcessPaymentRequest,
)
from . import payment_service
from .address_service import address_response
from .checkout_service import CURRENCY, Quote, build_quote, get_active_cart, get_cart_items, issue_response
from .errors import ServiceError
from .inventory_service import available_quantity, decrement_inventory
from .payment_method_service import find_user_payment_method, save_card
from .pricing_service import current_unit_price, money

PENDING_ORDER_TTL = timedelta(minutes=30)
MAX_PAYMENT_ATTEMPTS = 5
CLAIMABLE_PAYMENT_STATUSES = ("PENDING", "DECLINED", "FAILED")
VISIBLE_PAYMENT_STATUSES = ("PAID", "REFUNDED")


@dataclass
class ChargeCard:
    brand: str
    last4: str
    payment_method_id: int | None
    expiry_month: int
    expiry_year: int
    save: bool


class _StockShortage(Exception):
    def __init__(self, product_id: int) -> None:
        super().__init__(product_id)
        self.product_id = product_id


# ---------- lookups ----------

def get_user_order(db: Session, user: User, order_id: int) -> Order:
    order = db.query(Order).filter(Order.id == order_id, Order.user_id == user.id).first()
    if order is None:
        raise ServiceError(404, "ORDER_NOT_FOUND", "Order not found.")
    return order


def _order_items(db: Session, order_id: int) -> list[OrderItem]:
    return db.query(OrderItem).filter(OrderItem.order_id == order_id).order_by(OrderItem.id).all()


def _order_payment(db: Session, order_id: int) -> Payment | None:
    return db.query(Payment).filter(Payment.order_id == order_id).order_by(Payment.id.desc()).first()


def _order_fulfillment(db: Session, order_id: int) -> Fulfillment | None:
    return db.query(Fulfillment).filter(Fulfillment.order_id == order_id).order_by(Fulfillment.id.desc()).first()


def _attempt_count(db: Session, payment_id: int) -> int:
    return db.query(func.count(PaymentAttempt.id)).filter(PaymentAttempt.payment_id == payment_id).scalar()


def _add_history(db: Session, order_id: int, status: str, note: str) -> None:
    db.add(OrderStatusHistory(order_id=order_id, status=status, note=note, created_at=utc_now()))


# ---------- pending order lifecycle ----------

def cancel_order(db: Session, order: Order, note: str) -> None:
    now = utc_now()
    order.status = "CANCELLED"
    order.fulfillment_status = "CANCELLED"
    order.updated_at = now
    payment = _order_payment(db, order.id)
    if payment is not None and payment.status != "SUCCEEDED":
        payment.status = "CANCELLED"
        payment.updated_at = now
    fulfillment = _order_fulfillment(db, order.id)
    if fulfillment is not None:
        fulfillment.status = "CANCELLED"
        fulfillment.updated_at = now
    _add_history(db, order.id, "CANCELLED", note)
    db.flush()


def _is_stale(order: Order) -> bool:
    return order.status == "PENDING" and order.created_at < utc_now() - PENDING_ORDER_TTL


def expire_stale_pending_orders(db: Session, user_id: int) -> None:
    cutoff = utc_now() - PENDING_ORDER_TTL
    for order in db.query(Order).filter(Order.user_id == user_id, Order.status == "PENDING", Order.created_at < cutoff).all():
        cancel_order(db, order, "Checkout expired before payment was completed.")


def _matches_quote(db: Session, order: Order, quote: Quote) -> bool:
    order_lines = Counter((i.product_id, i.variant_id, i.quantity, money(i.unit_price)) for i in _order_items(db, order.id))
    quote_lines = Counter(
        (line.cart_item.product_id, line.cart_item.variant_id, line.cart_item.quantity, line.unit_price) for line in quote.lines
    )
    fulfillment = _order_fulfillment(db, order.id)
    return (
        order_lines == quote_lines
        and fulfillment is not None
        and fulfillment.type == quote.selection.fulfillment_type
        and fulfillment.store_id == quote.fulfillment_store.id
        and order.shipping_address_id == (quote.shipping_address.id if quote.shipping_address else None)
        and order.billing_address_id == quote.billing_address.id
        and money(order.total) == quote.total
    )


def _create_order_from_quote(db: Session, user: User, quote: Quote) -> Order:
    now = utc_now()
    order = Order(
        user_id=user.id,
        order_number=f"PENDING-{secrets.token_hex(8)}",
        status="PENDING",
        payment_status="PENDING",
        fulfillment_status="PENDING",
        shipping_address_id=quote.shipping_address.id if quote.shipping_address else None,
        billing_address_id=quote.billing_address.id,
        subtotal=float(quote.subtotal),
        discount=float(quote.discount),
        shipping_cost=float(quote.shipping_cost),
        tax=float(quote.tax),
        total=float(quote.total),
        currency=CURRENCY,
        created_at=now,
        updated_at=now,
    )
    db.add(order)
    db.flush()
    # Derived from the row ID, so it is unique without a separate counter.
    order.order_number = f"BM-{now:%Y%m%d}-{10000 + order.id:05d}"
    for line in quote.lines:
        db.add(OrderItem(
            order_id=order.id,
            product_id=line.cart_item.product_id,
            variant_id=line.cart_item.variant_id,
            product_name=line.product.name,
            sku=line.sku,
            quantity=line.cart_item.quantity,
            unit_price=float(line.unit_price),
            subtotal=float(line.line_total),
        ))
    db.add(Payment(
        order_id=order.id,
        amount=float(quote.total),
        currency=CURRENCY,
        provider=payment_service.PROVIDER,
        status="PENDING",
        created_at=now,
        updated_at=now,
    ))
    db.add(Fulfillment(
        order_id=order.id,
        type=quote.selection.fulfillment_type,
        store_id=quote.fulfillment_store.id,
        status="PENDING",
        estimated_date=quote.estimated_date,
        created_at=now,
        updated_at=now,
    ))
    db.flush()
    return order


def create_pending_order(db: Session, user: User, request: PlaceOrderRequest) -> tuple[Order, bool]:
    """Returns (order, created). Re-submitting the same checkout returns the existing draft."""
    expire_stale_pending_orders(db, user.id)
    quote = build_quote(db, user, request)
    blocking = quote.blocking_issues
    if any(issue.code == "EMPTY_CART" for issue in blocking):
        db.commit()
        raise ServiceError(400, "EMPTY_CART", "Your cart is empty.")
    if blocking:
        db.commit()
        raise ServiceError(409, "CHECKOUT_INVALID", blocking[0].message, issues=[issue_response(i).model_dump() for i in blocking])
    if money(request.expected_total) != quote.total:
        db.commit()
        raise ServiceError(
            409,
            "TOTAL_CHANGED",
            f"Your order total is now ${quote.total}. Please review it before placing your order.",
            total=float(quote.total),
        )

    for existing in db.query(Order).filter(Order.user_id == user.id, Order.status == "PENDING").all():
        if _matches_quote(db, existing, quote):
            db.commit()
            return existing, False
        cancel_order(db, existing, "Replaced by a new checkout.")

    order = _create_order_from_quote(db, user, quote)
    db.commit()
    return order, True


def pending_order_response(db: Session, order: Order) -> PendingOrderResponse:
    payment = _order_payment(db, order.id)
    used = _attempt_count(db, payment.id) if payment else 0
    return PendingOrderResponse(
        order_id=order.id,
        order_number=order.order_number,
        status=order.status,
        payment_status=order.payment_status,
        total=order.total,
        attempts_used=used,
        attempts_remaining=max(MAX_PAYMENT_ATTEMPTS - used, 0),
        expires_at=order.created_at + PENDING_ORDER_TTL,
    )


# ---------- payment ----------

def _resolve_card(db: Session, user: User, request: ProcessPaymentRequest) -> ChargeCard:
    if request.payment_method_id is not None:
        method = find_user_payment_method(db, user, request.payment_method_id)
        if method is None:
            raise ServiceError(404, "PAYMENT_METHOD_NOT_FOUND", "Payment method not found.")
        if payment_service.is_expired(method.expiry_month, method.expiry_year):
            raise ServiceError(422, "CARD_EXPIRED", "This card has expired. Please choose another payment method.")
        return ChargeCard(method.card_brand, method.last4, method.id, method.expiry_month, method.expiry_year, save=False)

    card = request.card
    check = payment_service.check_card(
        card.card_number.get_secret_value(), card.expiry_month, card.expiry_year, card.cvv.get_secret_value()
    )
    if not check.valid:
        raise ServiceError(422, "CARD_INVALID", "Please correct the card details.", errors=check.errors)
    return ChargeCard(check.brand, check.last4, None, card.expiry_month, card.expiry_year, save=request.save_card)


def _ensure_payable(db: Session, order: Order, payment: Payment) -> int:
    if order.status == "CANCELLED":
        raise ServiceError(409, "ORDER_CANCELLED", "This checkout is no longer active. Please place your order again.")
    if _is_stale(order):
        cancel_order(db, order, "Checkout expired before payment was completed.")
        db.commit()
        raise ServiceError(409, "ORDER_EXPIRED", "Your checkout expired. Please place your order again.")
    if payment.status == "PROCESSING":
        raise ServiceError(409, "PAYMENT_IN_PROGRESS", "A payment for this order is already being processed.")
    return _attempt_count(db, payment.id)


def _ensure_order_still_valid(db: Session, user: User, order: Order, items: list[OrderItem], store: Store) -> None:
    cart_lines = Counter((i.product_id, i.variant_id, i.quantity) for i in get_cart_items(db, get_active_cart(db, user)))
    order_lines = Counter((i.product_id, i.variant_id, i.quantity) for i in items)
    if cart_lines != order_lines:
        cancel_order(db, order, "Cart changed before payment.")
        db.commit()
        raise ServiceError(409, "CART_CHANGED", "Your cart changed since you started checkout. Please review your order and place it again.")

    for item in items:
        product = db.get(Product, item.product_id)
        if product is None or not product.is_active:
            cancel_order(db, order, f"{item.product_name} became unavailable before payment.")
            db.commit()
            raise ServiceError(409, "PRODUCT_UNAVAILABLE", f"{item.product_name} is no longer available. Please review your order.")
        if current_unit_price(db, item.product_id, store.region_id) != money(item.unit_price):
            cancel_order(db, order, "A price changed before payment.")
            db.commit()
            raise ServiceError(409, "PRICE_CHANGED", "A price in your order changed. Please review your order and place it again.")

    shortages = [
        {"product_id": item.product_id, "product_name": item.product_name, "requested": item.quantity, "available": available}
        for item in items
        if (available := available_quantity(db, item.product_id, store.id)) < item.quantity
    ]
    if shortages:
        raise ServiceError(
            409,
            "INSUFFICIENT_INVENTORY",
            "Some items aren't available in the quantity you ordered. You have not been charged.",
            items=shortages,
        )


def _claim_payment(db: Session, payment_id: int) -> bool:
    """Atomically mark the payment as processing so a double-click can't charge twice."""
    result = db.execute(
        update(Payment)
        .where(Payment.id == payment_id, Payment.status.in_(CLAIMABLE_PAYMENT_STATUSES))
        .values(status="PROCESSING", updated_at=utc_now())
        .execution_options(synchronize_session=False)
    )
    db.commit()
    return result.rowcount == 1


def _release_claim(db: Session, payment_id: int, previous_status: str) -> None:
    db.execute(
        update(Payment)
        .where(Payment.id == payment_id, Payment.status == "PROCESSING")
        .values(status=previous_status, updated_at=utc_now())
        .execution_options(synchronize_session=False)
    )


def _confirm_order(
    db: Session,
    user: User,
    order: Order,
    payment: Payment,
    fulfillment: Fulfillment,
    store: Store,
    card: ChargeCard,
    result: payment_service.GatewayResult,
    attempt_number: int,
) -> None:
    now = utc_now()
    if card.save:
        method, _ = save_card(db, user, card.brand, card.last4, card.expiry_month, card.expiry_year, order.billing_address_id, make_default=False)
        card.payment_method_id = method.id

    db.add(PaymentAttempt(
        payment_id=payment.id,
        attempt_number=attempt_number,
        payment_method_id=card.payment_method_id,
        amount=order.total,
        status="SUCCEEDED",
        transaction_id=result.transaction_id,
        created_at=now,
    ))
    payment.status = "SUCCEEDED"
    payment.transaction_id = result.transaction_id
    payment.payment_method_id = card.payment_method_id
    payment.card_brand = card.brand
    payment.card_last4 = card.last4
    payment.failure_code = None
    payment.failure_message = None
    payment.updated_at = now

    ready_for_pickup = fulfillment.type == "STORE_PICKUP"
    fulfillment_status = "READY_FOR_PICKUP" if ready_for_pickup else "PROCESSING"
    order.status = "CONFIRMED"
    order.payment_status = "PAID"
    order.fulfillment_status = fulfillment_status
    order.updated_at = now
    fulfillment.status = fulfillment_status
    fulfillment.updated_at = now

    _add_history(db, order.id, "CONFIRMED", "Payment received and order confirmed.")
    _add_history(db, order.id, "PROCESSING", "Order sent to fulfillment.")
    if ready_for_pickup:
        _add_history(db, order.id, "READY_FOR_PICKUP", f"Ready for pickup at {store.name}.")

    cart = get_active_cart(db, user)
    if cart is not None:
        db.query(CartItem).filter(CartItem.cart_id == cart.id).delete(synchronize_session=False)
        cart.updated_at = now


def _record_failure(
    db: Session,
    order_id: int,
    payment_id: int,
    card: ChargeCard,
    result: payment_service.GatewayResult,
    attempt_number: int,
) -> None:
    now = utc_now()
    order = db.get(Order, order_id)
    payment = db.get(Payment, payment_id)
    db.add(PaymentAttempt(
        payment_id=payment_id,
        attempt_number=attempt_number,
        payment_method_id=card.payment_method_id,
        amount=order.total,
        status=result.attempt_status,
        transaction_id=result.transaction_id,
        failure_code=result.failure_code,
        failure_message=result.failure_message,
        created_at=now,
    ))
    payment.status = result.payment_status
    payment.payment_method_id = card.payment_method_id
    payment.card_brand = card.brand
    payment.card_last4 = card.last4
    payment.failure_code = result.failure_code
    payment.failure_message = result.failure_message
    payment.updated_at = now
    order.payment_status = result.payment_status
    order.updated_at = now
    if attempt_number >= MAX_PAYMENT_ATTEMPTS:
        cancel_order(db, order, "Payment failed too many times.")


def _payment_result(db: Session, order: Order, payment: Payment) -> PaymentResult:
    return PaymentResult(
        order_id=order.id,
        order_number=order.order_number,
        status=order.status,
        payment_status=order.payment_status,
        fulfillment_status=order.fulfillment_status,
        transaction_id=payment.transaction_id,
        attempt_number=_attempt_count(db, payment.id),
        total=order.total,
    )


def process_payment(db: Session, user: User, request: ProcessPaymentRequest) -> PaymentResult:
    order = get_user_order(db, user, request.order_id)
    payment = _order_payment(db, order.id)
    if order.payment_status == "PAID":
        return _payment_result(db, order, payment)
    attempts_used = _ensure_payable(db, order, payment)

    card = _resolve_card(db, user, request)
    fulfillment = _order_fulfillment(db, order.id)
    store = db.get(Store, fulfillment.store_id)
    items = _order_items(db, order.id)
    _ensure_order_still_valid(db, user, order, items, store)

    previous_status = payment.status
    if not _claim_payment(db, payment.id):
        db.expire_all()
        if db.get(Order, order.id).payment_status == "PAID":
            return _payment_result(db, order, payment)
        raise ServiceError(409, "PAYMENT_IN_PROGRESS", "A payment for this order is already being processed.")

    attempt_number = attempts_used + 1
    try:
        # Stock is taken first so the write lock is held through the charge; a decline rolls it back.
        for item in items:
            if not decrement_inventory(db, item.product_id, store.id, item.quantity):
                raise _StockShortage(item.product_id)
        result = payment_service.charge(card.last4, money(order.total), attempt_number)
        if result.succeeded:
            _confirm_order(db, user, order, payment, fulfillment, store, card, result, attempt_number)
            db.commit()
            return _payment_result(db, order, payment)
        db.rollback()
    except _StockShortage as shortage:
        db.rollback()
        _release_claim(db, payment.id, previous_status)
        db.commit()
        raise ServiceError(
            409,
            "INSUFFICIENT_INVENTORY",
            "An item in your order just sold out. You have not been charged.",
            items=[{"product_id": shortage.product_id}],
        )
    except Exception:
        db.rollback()
        _release_claim(db, payment.id, previous_status)
        db.commit()
        raise

    _record_failure(db, order.id, payment.id, card, result, attempt_number)
    db.commit()
    remaining = max(MAX_PAYMENT_ATTEMPTS - attempt_number, 0)
    raise ServiceError(
        402,
        result.failure_code,
        result.failure_message,
        order_id=order.id,
        attempt_number=attempt_number,
        attempts_remaining=remaining,
        can_retry=remaining > 0,
        transaction_id=result.transaction_id,
    )


def payment_detail(db: Session, user: User, transaction_id: str) -> PaymentDetailResponse:
    payment = db.query(Payment).filter(Payment.transaction_id == transaction_id).first()
    if payment is None:
        attempt = db.query(PaymentAttempt).filter(PaymentAttempt.transaction_id == transaction_id).first()
        payment = db.get(Payment, attempt.payment_id) if attempt else None
    order = db.get(Order, payment.order_id) if payment else None
    if order is None or order.user_id != user.id:
        raise ServiceError(404, "PAYMENT_NOT_FOUND", "Payment not found.")
    attempts = db.query(PaymentAttempt).filter(PaymentAttempt.payment_id == payment.id).order_by(PaymentAttempt.attempt_number).all()
    return PaymentDetailResponse(
        order_id=order.id,
        order_number=order.order_number,
        status=payment.status,
        amount=payment.amount,
        currency=payment.currency,
        transaction_id=payment.transaction_id,
        card_display=payment_service.card_display(payment.card_brand, payment.card_last4),
        attempts=[
            PaymentAttemptResponse(
                attempt_number=attempt.attempt_number,
                status=attempt.status,
                amount=attempt.amount,
                transaction_id=attempt.transaction_id,
                failure_code=attempt.failure_code,
                failure_message=attempt.failure_message,
                created_at=attempt.created_at,
            )
            for attempt in attempts
        ],
    )


# ---------- history ----------

def list_orders(db: Session, user: User, page: int, limit: int) -> OrderListResponse:
    expire_stale_pending_orders(db, user.id)
    db.commit()
    query = db.query(Order).filter(Order.user_id == user.id, Order.payment_status.in_(VISIBLE_PAYMENT_STATUSES))
    total = query.count()
    orders = query.order_by(Order.created_at.desc(), Order.id.desc()).offset((page - 1) * limit).limit(limit).all()
    summaries = []
    for order in orders:
        fulfillment = _order_fulfillment(db, order.id)
        item_count = db.query(func.coalesce(func.sum(OrderItem.quantity), 0)).filter(OrderItem.order_id == order.id).scalar()
        summaries.append(OrderSummaryResponse(
            order_id=order.id,
            order_number=order.order_number,
            created_at=order.created_at,
            total=order.total,
            status=order.status,
            payment_status=order.payment_status,
            fulfillment_status=order.fulfillment_status,
            fulfillment_type=fulfillment.type if fulfillment else None,
            item_count=item_count,
        ))
    return OrderListResponse(items=summaries, total=total, page=page, limit=limit)


def order_detail(db: Session, order: Order) -> OrderDetailResponse:
    payment = _order_payment(db, order.id)
    fulfillment = _order_fulfillment(db, order.id)
    store = db.get(Store, fulfillment.store_id) if fulfillment and fulfillment.store_id else None
    # Hidden (deleted) addresses are still shown on the orders that used them.
    shipping = db.get(Address, order.shipping_address_id) if order.shipping_address_id else None
    billing = db.get(Address, order.billing_address_id) if order.billing_address_id else None
    history = (
        db.query(OrderStatusHistory)
        .filter(OrderStatusHistory.order_id == order.id)
        .order_by(OrderStatusHistory.created_at, OrderStatusHistory.id)
        .all()
    )
    items = []
    for item in _order_items(db, order.id):
        product = db.get(Product, item.product_id)
        items.append(OrderItemResponse(
            product_id=item.product_id,
            variant_id=item.variant_id,
            product_name=item.product_name,
            sku=item.sku,
            quantity=item.quantity,
            unit_price=item.unit_price,
            subtotal=item.subtotal,
            image_url=product.image_url if product else None,
        ))
    return OrderDetailResponse(
        order_id=order.id,
        order_number=order.order_number,
        created_at=order.created_at,
        status=order.status,
        payment_status=order.payment_status,
        fulfillment_status=order.fulfillment_status,
        items=items,
        subtotal=order.subtotal,
        discount=order.discount,
        shipping_cost=order.shipping_cost,
        tax=order.tax,
        total=order.total,
        currency=order.currency,
        shipping_address=address_response(shipping) if shipping else None,
        billing_address=address_response(billing) if billing else None,
        payment=OrderPaymentResponse(
            status=payment.status,
            amount=payment.amount,
            card_brand=payment.card_brand,
            card_last4=payment.card_last4,
            card_display=payment_service.card_display(payment.card_brand, payment.card_last4),
            transaction_id=payment.transaction_id,
        ) if payment else None,
        fulfillment=OrderFulfillmentResponse(
            type=fulfillment.type,
            status=fulfillment.status,
            estimated_date=fulfillment.estimated_date,
            tracking_number=fulfillment.tracking_number,
            store_id=store.id if store else None,
            store_name=store.name if store else None,
            store_address=f"{store.address}, {store.city}, {store.state} {store.zip_code}" if store else None,
        ) if fulfillment else None,
        timeline=[OrderStatusEvent(status=event.status, note=event.note, created_at=event.created_at) for event in history],
    )
