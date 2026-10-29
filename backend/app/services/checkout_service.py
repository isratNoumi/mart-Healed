from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from ..models import Address, Cart, CartItem, Product, ProductVariant, Region, Store, User
from ..schemas import CheckoutIssue, CheckoutLine, CheckoutQuote, CheckoutSelection, FulfillmentOption
from .address_service import BILLING_TYPES, SHIPPING_TYPES, find_user_address
from .fulfillment_service import StockLine, estimated_date, fulfillment_options, shipping_cost
from .inventory_service import available_quantity
from .location_service import get_active_store, get_region, zip_in_region
from .pricing_service import ZERO, current_unit_price, money, tax_for

CURRENCY = "USD"


@dataclass
class Issue:
    code: str
    message: str
    blocking: bool = True
    product_id: int | None = None
    available_quantity: int | None = None


@dataclass
class QuoteLine:
    cart_item: CartItem
    product: Product | None
    variant: ProductVariant | None
    unit_price: Decimal | None
    available: int

    @property
    def line_total(self) -> Decimal | None:
        return money(self.unit_price * self.cart_item.quantity) if self.unit_price is not None else None

    @property
    def sku(self) -> str:
        return self.variant.sku if self.variant else self.product.sku


@dataclass
class Quote:
    selection: CheckoutSelection
    selected_store: Store
    region: Region
    lines: list[QuoteLine]
    issues: list[Issue]
    fulfillment_store: Store | None
    shipping_address: Address | None
    billing_address: Address | None
    subtotal: Decimal
    discount: Decimal
    shipping_cost: Decimal
    tax: Decimal
    total: Decimal
    estimated_date: date | None

    @property
    def blocking_issues(self) -> list[Issue]:
        return [issue for issue in self.issues if issue.blocking]

    @property
    def stock_lines(self) -> list[StockLine]:
        return [StockLine(line.cart_item.product_id, line.cart_item.quantity) for line in self.lines]


def get_active_cart(db: Session, user: User) -> Cart | None:
    return db.query(Cart).filter(Cart.user_id == user.id, Cart.status == "active").first()


def get_cart_items(db: Session, cart: Cart | None) -> list[CartItem]:
    if cart is None:
        return []
    return db.query(CartItem).filter(CartItem.cart_id == cart.id).order_by(CartItem.id).all()


def _resolve_address(db: Session, user: User, address_id: int, allowed_types: tuple[str, ...], purpose: str, issues: list[Issue]) -> Address | None:
    address = find_user_address(db, user, address_id)
    if address is None:
        issues.append(Issue("ADDRESS_NOT_FOUND", f"The selected {purpose} address could not be found."))
        return None
    if address.type not in allowed_types:
        issues.append(Issue("ADDRESS_TYPE_INVALID", f"This address can't be used as a {purpose} address."))
        return None
    return address


def build_quote(db: Session, user: User, selection: CheckoutSelection) -> Quote:
    """Price the user's cart for the given selections. Never writes to the database."""
    selected_store = get_active_store(db, selection.store_id)
    region = get_region(db, selected_store.region_id)
    fulfillment_type = selection.fulfillment_type
    issues: list[Issue] = []

    if fulfillment_type is None:
        issues.append(Issue("FULFILLMENT_REQUIRED", "Choose how you'd like to receive your order."))

    pickup_store = None
    if fulfillment_type == "STORE_PICKUP":
        if selection.pickup_store_id is None:
            issues.append(Issue("PICKUP_STORE_REQUIRED", "Choose a store for pickup."))
        else:
            pickup_store = db.query(Store).filter(Store.id == selection.pickup_store_id, Store.is_active == 1).first()
            if pickup_store is None or pickup_store.region_id != selected_store.region_id:
                issues.append(Issue("PICKUP_STORE_INVALID", f"Pickup is only available at stores in the {region.name} area."))
                pickup_store = None
    fulfillment_store = pickup_store if fulfillment_type == "STORE_PICKUP" else selected_store
    stock_store = fulfillment_store or selected_store

    shipping_address = None
    if selection.shipping_address_id is not None:
        shipping_address = _resolve_address(db, user, selection.shipping_address_id, SHIPPING_TYPES, "shipping", issues)
    elif fulfillment_type in ("SHIP_TO_HOME", "DELIVERY"):
        issues.append(Issue("SHIPPING_ADDRESS_REQUIRED", "Choose a shipping address."))

    if selection.billing_address_id is not None:
        billing_address = _resolve_address(db, user, selection.billing_address_id, BILLING_TYPES, "billing", issues)
    else:
        billing_address = shipping_address
        if billing_address is None and selection.shipping_address_id is None:
            issues.append(Issue("BILLING_ADDRESS_REQUIRED", "Choose a billing address."))

    if fulfillment_type == "DELIVERY" and shipping_address is not None and not zip_in_region(shipping_address.zip_code, region):
        issues.append(Issue("DELIVERY_OUT_OF_AREA", f"Delivery is only available to addresses in the {region.name} area."))

    items = get_cart_items(db, get_active_cart(db, user))
    if not items:
        issues.append(Issue("EMPTY_CART", "Your cart is empty."))

    lines: list[QuoteLine] = []
    for item in items:
        product = db.get(Product, item.product_id)
        variant = db.get(ProductVariant, item.variant_id) if item.variant_id else None
        name = product.name if product else "An item in your cart"
        unit_price = None
        if product is None or not product.is_active:
            issues.append(Issue("PRODUCT_UNAVAILABLE", f"{name} is no longer available.", product_id=item.product_id))
        elif item.variant_id is not None and (variant is None or variant.product_id != product.id):
            issues.append(Issue("VARIANT_UNAVAILABLE", f"The selected option for {name} is no longer available.", product_id=item.product_id))
        else:
            unit_price = current_unit_price(db, item.product_id, region.id)
            if unit_price is None:
                issues.append(Issue("NOT_SOLD_IN_REGION", f"{name} isn't sold in the {region.name} area.", product_id=item.product_id))

        available = available_quantity(db, item.product_id, stock_store.id)
        if unit_price is not None and item.quantity > available:
            issues.append(Issue(
                "INSUFFICIENT_INVENTORY",
                f"Only {available} of {name} available at {stock_store.name}.",
                product_id=item.product_id,
                available_quantity=available,
            ))
        if unit_price is not None and money(item.unit_price) != unit_price:
            issues.append(Issue(
                "PRICE_CHANGED",
                f"The price of {name} changed from ${money(item.unit_price)} to ${unit_price}.",
                blocking=False,
                product_id=item.product_id,
            ))
        lines.append(QuoteLine(item, product, variant, unit_price, available))

    subtotal = sum((line.line_total for line in lines if line.line_total is not None), ZERO)
    discount = ZERO
    shipping = shipping_cost(fulfillment_type, subtotal)
    if fulfillment_type == "STORE_PICKUP":
        tax_state = pickup_store.state if pickup_store else selected_store.state
    else:
        tax_state = shipping_address.state if shipping_address else selected_store.state
    tax = tax_for(subtotal - discount, tax_state)

    return Quote(
        selection=selection,
        selected_store=selected_store,
        region=region,
        lines=lines,
        issues=issues,
        fulfillment_store=fulfillment_store,
        shipping_address=shipping_address,
        billing_address=billing_address,
        subtotal=subtotal,
        discount=discount,
        shipping_cost=shipping,
        tax=tax,
        total=subtotal - discount + shipping + tax,
        estimated_date=estimated_date(fulfillment_type) if fulfillment_type else None,
    )


def issue_response(issue: Issue) -> CheckoutIssue:
    return CheckoutIssue(
        code=issue.code,
        message=issue.message,
        blocking=issue.blocking,
        product_id=issue.product_id,
        available_quantity=issue.available_quantity,
    )


def quote_response(quote: Quote) -> CheckoutQuote:
    return CheckoutQuote(
        store_id=quote.selected_store.id,
        fulfillment_type=quote.selection.fulfillment_type,
        pickup_store_id=quote.fulfillment_store.id if quote.selection.fulfillment_type == "STORE_PICKUP" and quote.fulfillment_store else None,
        shipping_address_id=quote.shipping_address.id if quote.shipping_address else None,
        billing_address_id=quote.billing_address.id if quote.billing_address else None,
        lines=[
            CheckoutLine(
                cart_item_id=line.cart_item.id,
                product_id=line.cart_item.product_id,
                variant_id=line.cart_item.variant_id,
                product_name=line.product.name if line.product else "Unavailable product",
                variant_name=line.variant.name if line.variant else None,
                image_url=line.product.image_url if line.product else None,
                quantity=line.cart_item.quantity,
                unit_price=float(line.unit_price) if line.unit_price is not None else None,
                previous_unit_price=float(money(line.cart_item.unit_price)),
                line_total=float(line.line_total) if line.line_total is not None else None,
                available_quantity=line.available,
            )
            for line in quote.lines
        ],
        issues=[issue_response(issue) for issue in quote.issues],
        subtotal=float(quote.subtotal),
        discount=float(quote.discount),
        shipping_cost=float(quote.shipping_cost),
        tax=float(quote.tax),
        total=float(quote.total),
        currency=CURRENCY,
        estimated_date=quote.estimated_date,
        can_place_order=not quote.blocking_issues,
    )


def options_for_quote(db: Session, quote: Quote) -> list[FulfillmentOption]:
    return fulfillment_options(db, quote.selected_store, quote.region, quote.stock_lines, quote.subtotal, quote.shipping_address)
