import hashlib
import secrets

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from ..clock import utc_now
from ..database import get_db
from ..dependencies import get_optional_user
from ..models import Cart, CartItem, Product, ProductVariant, User
from ..schemas import CartItemRequest, CartItemResponse, CartQuantityRequest, CartResponse
from ..services.inventory_service import available_quantity
from ..services.location_service import resolve_store_context as resolve_context
from ..services.auth_service import SECURE_COOKIES
from ..services.pricing_service import current_unit_price

router = APIRouter(prefix="/api/cart", tags=["cart"])

# Guest carts are bound to a server-issued, unguessable, HttpOnly cookie. Client-supplied
# identifiers (e.g. a ``session_id`` query parameter) are never trusted.
GUEST_CART_COOKIE = "bm_cart"
GUEST_CART_LIFETIME_SECONDS = 30 * 24 * 60 * 60


def _hash_cart_token(token: str) -> str:
    return "guest:" + hashlib.sha256(token.encode()).hexdigest()


def _valid_cart_token(token: str | None) -> bool:
    return bool(token) and 20 <= len(token) <= 128


def resolve_cart(db: Session, response: Response, cart_token: str | None, user: User | None) -> Cart:
    """Return the caller's cart, identified only by the authenticated user or the
    server-issued guest cart cookie."""
    token = cart_token if _valid_cart_token(cart_token) else None
    if user is not None:
        cart = get_or_create_cart(db, _hash_cart_token(token) if token else None, user)
        if token:
            # Guest cart (if any) has been merged into the user's cart; drop the guest binding.
            response.delete_cookie(GUEST_CART_COOKIE, path="/api/cart", httponly=True, samesite="lax", secure=SECURE_COOKIES)
        return cart
    if token is None:
        token = secrets.token_urlsafe(32)
        response.set_cookie(
            GUEST_CART_COOKIE,
            token,
            max_age=GUEST_CART_LIFETIME_SECONDS,
            httponly=True,
            samesite="lax",
            secure=SECURE_COOKIES,
            path="/api/cart",
        )
    return get_or_create_cart(db, _hash_cart_token(token), None)


def merge_guest_cart(db: Session, guest_cart: Cart, user_cart: Cart) -> None:
    for item in db.query(CartItem).filter(CartItem.cart_id == guest_cart.id).all():
        existing = db.query(CartItem).filter_by(cart_id=user_cart.id, product_id=item.product_id, variant_id=item.variant_id).first()
        if existing:
            existing.quantity += item.quantity
            existing.updated_at = utc_now()
            db.delete(item)
        else:
            item.cart_id = user_cart.id
    db.flush()
    db.delete(guest_cart)
    user_cart.updated_at = utc_now()


def get_or_create_cart(db: Session, session_id: str | None, user: User | None = None) -> Cart:
    guest_cart = None
    if session_id:
        guest_cart = db.query(Cart).filter(Cart.session_id == session_id, Cart.user_id.is_(None), Cart.status == "active").first()
    if user is None:
        if not session_id:
            raise HTTPException(status_code=401, detail="Cart session required.")
        if guest_cart:
            return guest_cart
        cart = Cart(session_id=session_id, status="active", created_at=utc_now(), updated_at=utc_now())
        db.add(cart)
        db.flush()
        return cart

    cart = db.query(Cart).filter(Cart.user_id == user.id, Cart.status == "active").first()
    if cart is None:
        cart = Cart(user_id=user.id, status="active", created_at=utc_now(), updated_at=utc_now())
        db.add(cart)
        db.flush()
    if guest_cart:
        merge_guest_cart(db, guest_cart, cart)
    return cart


def cart_response(db: Session, cart: Cart) -> CartResponse:
    items = []
    for item in db.query(CartItem).filter(CartItem.cart_id == cart.id).order_by(CartItem.id).all():
        product = db.get(Product, item.product_id)
        variant = db.get(ProductVariant, item.variant_id) if item.variant_id else None
        items.append(CartItemResponse(
            id=item.id,
            product_id=item.product_id,
            product_name=product.name if product else "Unavailable product",
            image_url=product.image_url if product else None,
            variant_id=item.variant_id,
            variant_name=variant.name if variant else None,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total=round(item.quantity * item.unit_price, 2),
        ))
    return CartResponse(
        id=cart.id,
        items=items,
        item_count=sum(item.quantity for item in items),
        subtotal=round(sum(item.total for item in items), 2),
    )


def refresh_cart_prices(db: Session, cart: Cart, region_id: int, store_id: int) -> None:
    for item in db.query(CartItem).filter(CartItem.cart_id == cart.id).all():
        price = current_unit_price(db, item.product_id, region_id)
        if price is None:
            continue
        item.unit_price = float(price)
        available = available_quantity(db, item.product_id, store_id)
        # Out-of-stock items keep their quantity (it can't be 0); checkout blocks them instead.
        if 0 < available < item.quantity:
            item.quantity = available
        item.updated_at = utc_now()


def validate_item(
    db: Session,
    product_id: int,
    variant_id: int | None,
    quantity: int,
    region_id: int,
    store_id: int,
) -> tuple[Product, float]:
    product = db.query(Product).filter(Product.id == product_id, Product.is_active == 1).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if variant_id is not None and not db.query(ProductVariant).filter(ProductVariant.id == variant_id, ProductVariant.product_id == product_id).first():
        raise HTTPException(status_code=400, detail="Variant does not belong to this product")
    price = current_unit_price(db, product_id, region_id)
    if price is None:
        raise HTTPException(status_code=400, detail="This product is not available in the selected region")
    available = available_quantity(db, product_id, store_id)
    if quantity > available:
        raise HTTPException(status_code=409, detail=f"Only {available} units are available")
    return product, float(price)


@router.get("", response_model=CartResponse)
def get_cart(
    response: Response,
    region_id: int | None = None,
    store_id: int | None = None,
    zip_code: str | None = None,
    cart_token: str | None = Cookie(default=None, alias=GUEST_CART_COOKIE),
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    cart = resolve_cart(db, response, cart_token, user)
    if region_id is not None or store_id is not None or zip_code:
        selected_region, selected_store = resolve_context(db, region_id, store_id, zip_code)
        refresh_cart_prices(db, cart, selected_region, selected_store)
    db.commit()
    return cart_response(db, cart)


@router.post("/items", response_model=CartResponse, status_code=201)
def add_cart_item(payload: CartItemRequest, response: Response, cart_token: str | None = Cookie(default=None, alias=GUEST_CART_COOKIE), user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    region_id, store_id = resolve_context(db, payload.region_id, payload.store_id, payload.zip_code)
    cart = resolve_cart(db, response, cart_token, user)
    existing = db.query(CartItem).filter_by(cart_id=cart.id, product_id=payload.product_id, variant_id=payload.variant_id).first()
    requested_quantity = payload.quantity + (existing.quantity if existing else 0)
    _, unit_price = validate_item(db, payload.product_id, payload.variant_id, requested_quantity, region_id, store_id)
    if existing:
        existing.quantity = requested_quantity
        existing.unit_price = unit_price
        existing.updated_at = utc_now()
    else:
        db.add(CartItem(cart_id=cart.id, product_id=payload.product_id, variant_id=payload.variant_id, quantity=payload.quantity, unit_price=unit_price, added_at=utc_now(), updated_at=utc_now()))
    cart.updated_at = utc_now()
    db.commit()
    return cart_response(db, cart)


@router.patch("/items/{item_id}", response_model=CartResponse)
def update_cart_item(item_id: int, payload: CartQuantityRequest, response: Response, cart_token: str | None = Cookie(default=None, alias=GUEST_CART_COOKIE), user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    region_id, store_id = resolve_context(db, payload.region_id, payload.store_id)
    cart = resolve_cart(db, response, cart_token, user)
    item = db.query(CartItem).filter(CartItem.id == item_id, CartItem.cart_id == cart.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    _, unit_price = validate_item(db, item.product_id, item.variant_id, payload.quantity, region_id, store_id)
    item.quantity = payload.quantity
    item.unit_price = unit_price
    item.updated_at = utc_now()
    cart.updated_at = utc_now()
    db.commit()
    return cart_response(db, cart)


@router.delete("/items/{item_id}", response_model=CartResponse)
def remove_cart_item(item_id: int, response: Response, cart_token: str | None = Cookie(default=None, alias=GUEST_CART_COOKIE), user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    cart = resolve_cart(db, response, cart_token, user)
    item = db.query(CartItem).filter(CartItem.id == item_id, CartItem.cart_id == cart.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    db.delete(item)
    cart.updated_at = utc_now()
    db.commit()
    return cart_response(db, cart)