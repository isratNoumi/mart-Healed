from datetime import date, datetime

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String)
    last_name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String)
    password_hash: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column()


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    token_hash: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column()
    expires_at: Mapped[datetime] = mapped_column()


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))
    name: Mapped[str] = mapped_column(String)
    slug: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text)


class Brand(Base):
    __tablename__ = "brands"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    slug: Mapped[str] = mapped_column(String)


class Region(Base):
    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    state: Mapped[str] = mapped_column(String)
    country: Mapped[str] = mapped_column(String)
    zip_start: Mapped[str] = mapped_column(String)
    zip_end: Mapped[str] = mapped_column(String)


class Store(Base):
    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    region_id: Mapped[int] = mapped_column(ForeignKey("regions.id"))
    store_number: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    address: Mapped[str] = mapped_column(String)
    city: Mapped[str] = mapped_column(String)
    state: Mapped[str] = mapped_column(String)
    zip_code: Mapped[str] = mapped_column(String)
    phone: Mapped[str | None] = mapped_column(String)
    is_active: Mapped[int] = mapped_column(Integer)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"))
    sku: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    slug: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text)
    short_description: Mapped[str | None] = mapped_column(Text)
    model_number: Mapped[str | None] = mapped_column(String)
    rating: Mapped[float] = mapped_column(Float)
    review_count: Mapped[int] = mapped_column(Integer)
    image_url: Mapped[str | None] = mapped_column(String)
    is_active: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column()


class ProductVariant(Base):
    __tablename__ = "product_variants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    sku: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    size: Mapped[str | None] = mapped_column(String)
    color: Mapped[str | None] = mapped_column(String)
    voltage: Mapped[str | None] = mapped_column(String)
    is_default: Mapped[int] = mapped_column(Integer)


class RegionalPrice(Base):
    __tablename__ = "regional_prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    region_id: Mapped[int] = mapped_column(ForeignKey("regions.id"))
    price: Mapped[float] = mapped_column(Float)
    sale_price: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String)
    updated_at: Mapped[datetime] = mapped_column()


class Inventory(Base):
    __tablename__ = "inventory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    quantity: Mapped[int] = mapped_column(Integer)
    reserved_quantity: Mapped[int] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column()


class Cart(Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    session_id: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column()
    updated_at: Mapped[datetime] = mapped_column()


class CartItem(Base):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    variant_id: Mapped[int | None] = mapped_column(ForeignKey("product_variants.id"))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[float] = mapped_column(Float)
    added_at: Mapped[datetime] = mapped_column()
    updated_at: Mapped[datetime] = mapped_column()


class Address(Base):
    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    type: Mapped[str] = mapped_column(String)
    first_name: Mapped[str] = mapped_column(String)
    last_name: Mapped[str] = mapped_column(String)
    address_line1: Mapped[str] = mapped_column(String)
    address_line2: Mapped[str | None] = mapped_column(String)
    city: Mapped[str] = mapped_column(String)
    state: Mapped[str] = mapped_column(String)
    zip_code: Mapped[str] = mapped_column(String)
    phone: Mapped[str | None] = mapped_column(String)
    is_default: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column()
    updated_at: Mapped[datetime] = mapped_column()
    deleted_at: Mapped[datetime | None] = mapped_column()


class PaymentMethod(Base):
    __tablename__ = "payment_methods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    type: Mapped[str] = mapped_column(String)
    card_brand: Mapped[str] = mapped_column(String)
    last4: Mapped[str] = mapped_column(String)
    expiry_month: Mapped[int] = mapped_column(Integer)
    expiry_year: Mapped[int] = mapped_column(Integer)
    billing_address_id: Mapped[int | None] = mapped_column(ForeignKey("addresses.id"))
    is_default: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column()


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    order_number: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    payment_status: Mapped[str] = mapped_column(String)
    fulfillment_status: Mapped[str] = mapped_column(String)
    shipping_address_id: Mapped[int | None] = mapped_column(ForeignKey("addresses.id"))
    billing_address_id: Mapped[int | None] = mapped_column(ForeignKey("addresses.id"))
    subtotal: Mapped[float] = mapped_column(Float)
    discount: Mapped[float] = mapped_column(Float)
    shipping_cost: Mapped[float] = mapped_column(Float)
    tax: Mapped[float] = mapped_column(Float)
    total: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column()
    updated_at: Mapped[datetime] = mapped_column()


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    variant_id: Mapped[int | None] = mapped_column(ForeignKey("product_variants.id"))
    product_name: Mapped[str] = mapped_column(String)
    sku: Mapped[str] = mapped_column(String)
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[float] = mapped_column(Float)
    subtotal: Mapped[float] = mapped_column(Float)


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    payment_method_id: Mapped[int | None] = mapped_column(ForeignKey("payment_methods.id"))
    card_brand: Mapped[str | None] = mapped_column(String)
    card_last4: Mapped[str | None] = mapped_column(String)
    transaction_id: Mapped[str | None] = mapped_column(String)
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String)
    provider: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    failure_code: Mapped[str | None] = mapped_column(String)
    failure_message: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column()
    updated_at: Mapped[datetime] = mapped_column()


class PaymentAttempt(Base):
    __tablename__ = "payment_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"))
    attempt_number: Mapped[int] = mapped_column(Integer)
    payment_method_id: Mapped[int | None] = mapped_column(ForeignKey("payment_methods.id"))
    amount: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String)
    transaction_id: Mapped[str | None] = mapped_column(String)
    failure_code: Mapped[str | None] = mapped_column(String)
    failure_message: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column()


class Fulfillment(Base):
    __tablename__ = "fulfillments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    type: Mapped[str] = mapped_column(String)
    store_id: Mapped[int | None] = mapped_column(ForeignKey("stores.id"))
    status: Mapped[str] = mapped_column(String)
    estimated_date: Mapped[date | None] = mapped_column()
    tracking_number: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column()
    updated_at: Mapped[datetime] = mapped_column()


class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    status: Mapped[str] = mapped_column(String)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column()