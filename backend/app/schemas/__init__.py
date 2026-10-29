import re
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, SecretStr, StringConstraints, field_validator, model_validator


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PersonName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]


def normalize_email(value: str) -> str:
    email = value.strip().lower()
    if len(email) > 254 or not EMAIL_PATTERN.match(email):
        raise ValueError("Enter a valid email address.")
    return email


class RegisterRequest(BaseModel):
    first_name: PersonName
    last_name: PersonName
    email: str
    # Upper bound keeps very large inputs from tying up the password hasher.
    password: str = Field(min_length=8, max_length=128)

    _normalize_email = field_validator("email")(normalize_email)


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=128)

    _normalize_email = field_validator("email")(normalize_email)


class UserResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str


class AuthResponse(BaseModel):
    user: UserResponse | None


class CategoryResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None = None


class BrandResponse(BaseModel):
    id: int
    name: str
    slug: str


class VariantResponse(BaseModel):
    id: int
    sku: str
    name: str
    size: str | None = None
    color: str | None = None
    voltage: str | None = None
    is_default: bool


class PriceResponse(BaseModel):
    price: float
    sale_price: float | None = None
    current_price: float
    currency: str
    region_id: int


class AvailabilityResponse(BaseModel):
    store_id: int
    store_name: str
    available_quantity: int
    in_stock: bool
    status: str


class ProductResponse(BaseModel):
    id: int
    sku: str
    name: str
    slug: str
    description: str | None = None
    short_description: str | None = None
    model_number: str | None = None
    rating: float
    review_count: int
    image_url: str | None = None
    brand: BrandResponse
    category: CategoryResponse
    price: PriceResponse | None = None
    availability: AvailabilityResponse | None = None
    variants: list[VariantResponse] = []


class ProductListResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    page: int
    limit: int


class RegionResponse(BaseModel):
    id: int
    name: str
    state: str
    country: str
    zip_start: str
    zip_end: str


class StoreResponse(BaseModel):
    id: int
    region_id: int
    store_number: str
    name: str
    address: str
    city: str
    state: str
    zip_code: str
    phone: str | None = None


class LocationResponse(BaseModel):
    zip_code: str
    region: RegionResponse
    store: StoreResponse


class CartItemRequest(BaseModel):
    product_id: int
    variant_id: int | None = None
    quantity: int = Field(ge=1)
    region_id: int | None = None
    store_id: int | None = None
    zip_code: str | None = None


class CartQuantityRequest(BaseModel):
    quantity: int = Field(ge=1)
    region_id: int | None = None
    store_id: int | None = None


class CartItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    image_url: str | None = None
    variant_id: int | None
    variant_name: str | None
    quantity: int
    unit_price: float
    total: float


class CartResponse(BaseModel):
    id: int
    items: list[CartItemResponse]
    item_count: int
    subtotal: float


US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS",
    "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC",
    "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
}
ZIP_PATTERN = re.compile(r"^\d{5}(-\d{4})?$")
AddressLine = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
FulfillmentType = Literal["SHIP_TO_HOME", "STORE_PICKUP", "DELIVERY"]


class AddressRequest(BaseModel):
    type: Literal["shipping", "billing", "both"] = "both"
    first_name: PersonName
    last_name: PersonName
    address_line1: AddressLine
    address_line2: Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)] | None = None
    city: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
    state: str
    zip_code: str
    phone: str
    is_default: bool = False

    @field_validator("address_line2")
    @classmethod
    def blank_line2_to_none(cls, value: str | None) -> str | None:
        return value or None

    @field_validator("state")
    @classmethod
    def valid_state(cls, value: str) -> str:
        state = value.strip().upper()
        if state not in US_STATES:
            raise ValueError("Enter a valid 2-letter US state code.")
        return state

    @field_validator("zip_code")
    @classmethod
    def valid_zip(cls, value: str) -> str:
        zip_code = value.strip()
        if not ZIP_PATTERN.match(zip_code):
            raise ValueError("Enter a 5-digit ZIP code or ZIP+4.")
        return zip_code

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, value: str) -> str:
        digits = re.sub(r"\D", "", value)
        if len(digits) == 11 and digits.startswith("1"):
            digits = digits[1:]
        if len(digits) != 10:
            raise ValueError("Enter a 10-digit US phone number.")
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"


class AddressResponse(BaseModel):
    id: int
    type: str
    first_name: str
    last_name: str
    address_line1: str
    address_line2: str | None
    city: str
    state: str
    zip_code: str
    phone: str | None
    is_default: bool


class CardInput(BaseModel):
    cardholder_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    card_number: SecretStr = Field(max_length=30)
    expiry_month: int = Field(ge=1, le=12)
    expiry_year: int = Field(ge=2000, le=2100)
    cvv: SecretStr = Field(max_length=4)


class PaymentMethodRequest(CardInput):
    billing_address_id: int | None = None
    is_default: bool = False


class PaymentMethodResponse(BaseModel):
    id: int
    card_brand: str
    last4: str
    expiry_month: int
    expiry_year: int
    billing_address_id: int | None
    is_default: bool
    is_expired: bool
    display: str


class CardValidationResponse(BaseModel):
    valid: bool
    brand: str | None
    last4: str | None
    errors: dict[str, str]


class CheckoutSelection(BaseModel):
    store_id: int
    fulfillment_type: FulfillmentType | None = None
    pickup_store_id: int | None = None
    shipping_address_id: int | None = None
    # Omit to bill to the shipping address.
    billing_address_id: int | None = None


class PlaceOrderRequest(CheckoutSelection):
    fulfillment_type: FulfillmentType
    # Total the customer saw; the order is refused if the server's total differs.
    expected_total: float = Field(ge=0)


class CheckoutIssue(BaseModel):
    code: str
    message: str
    blocking: bool
    product_id: int | None = None
    available_quantity: int | None = None


class CheckoutLine(BaseModel):
    cart_item_id: int
    product_id: int
    variant_id: int | None
    product_name: str
    variant_name: str | None
    image_url: str | None
    quantity: int
    unit_price: float | None
    previous_unit_price: float
    line_total: float | None
    available_quantity: int


class CheckoutQuote(BaseModel):
    store_id: int
    fulfillment_type: FulfillmentType | None
    pickup_store_id: int | None
    shipping_address_id: int | None
    billing_address_id: int | None
    lines: list[CheckoutLine]
    issues: list[CheckoutIssue]
    subtotal: float
    discount: float
    shipping_cost: float
    tax: float
    total: float
    currency: str
    estimated_date: date | None
    can_place_order: bool


class PickupStoreOption(BaseModel):
    store_id: int
    name: str
    address: str
    city: str
    state: str
    zip_code: str
    all_items_available: bool
    unavailable_product_ids: list[int]


class FulfillmentOption(BaseModel):
    type: FulfillmentType
    label: str
    available: bool
    reason: str | None
    cost: float
    estimated_date: date
    pickup_stores: list[PickupStoreOption] = []


class CheckoutResponse(BaseModel):
    quote: CheckoutQuote
    addresses: list[AddressResponse]
    payment_methods: list[PaymentMethodResponse]
    fulfillment_options: list[FulfillmentOption]


class PendingOrderResponse(BaseModel):
    order_id: int
    order_number: str
    status: str
    payment_status: str
    total: float
    attempts_used: int
    attempts_remaining: int
    expires_at: datetime


class ProcessPaymentRequest(BaseModel):
    order_id: int
    payment_method_id: int | None = None
    card: CardInput | None = None
    save_card: bool = False

    @model_validator(mode="after")
    def one_payment_source(self) -> "ProcessPaymentRequest":
        if (self.payment_method_id is None) == (self.card is None):
            raise ValueError("Provide either a saved payment method or new card details.")
        return self


class PaymentResult(BaseModel):
    order_id: int
    order_number: str
    status: str
    payment_status: str
    fulfillment_status: str
    transaction_id: str | None
    attempt_number: int
    total: float


class PaymentAttemptResponse(BaseModel):
    attempt_number: int
    status: str
    amount: float
    transaction_id: str | None
    failure_code: str | None
    failure_message: str | None
    created_at: datetime


class PaymentDetailResponse(BaseModel):
    order_id: int
    order_number: str
    status: str
    amount: float
    currency: str
    transaction_id: str | None
    card_display: str | None
    attempts: list[PaymentAttemptResponse]


class OrderSummaryResponse(BaseModel):
    order_id: int
    order_number: str
    created_at: datetime
    total: float
    status: str
    payment_status: str
    fulfillment_status: str
    fulfillment_type: str | None
    item_count: int


class OrderListResponse(BaseModel):
    items: list[OrderSummaryResponse]
    total: int
    page: int
    limit: int


class OrderItemResponse(BaseModel):
    product_id: int
    variant_id: int | None
    product_name: str
    sku: str
    quantity: int
    unit_price: float
    subtotal: float
    image_url: str | None


class OrderPaymentResponse(BaseModel):
    status: str
    amount: float
    card_brand: str | None
    card_last4: str | None
    card_display: str | None
    transaction_id: str | None


class OrderFulfillmentResponse(BaseModel):
    type: str
    status: str
    estimated_date: date | None
    tracking_number: str | None
    store_id: int | None
    store_name: str | None
    store_address: str | None


class OrderStatusEvent(BaseModel):
    status: str
    note: str | None
    created_at: datetime


class OrderDetailResponse(BaseModel):
    order_id: int
    order_number: str
    created_at: datetime
    status: str
    payment_status: str
    fulfillment_status: str
    items: list[OrderItemResponse]
    subtotal: float
    discount: float
    shipping_cost: float
    tax: float
    total: float
    currency: str
    shipping_address: AddressResponse | None
    billing_address: AddressResponse | None
    payment: OrderPaymentResponse | None
    fulfillment: OrderFulfillmentResponse | None
    timeline: list[OrderStatusEvent]