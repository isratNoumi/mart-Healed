from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import require_user
from ..models import User
from ..schemas import CheckoutQuote, CheckoutResponse, CheckoutSelection, FulfillmentOption
from ..services.address_service import SHIPPING_TYPES, address_response, list_addresses
from ..services.checkout_service import build_quote, options_for_quote, quote_response
from ..services.payment_method_service import list_payment_methods, payment_method_response

router = APIRouter(prefix="/api", tags=["checkout"])


@router.get("/checkout", response_model=CheckoutResponse)
def get_checkout(
    selection: Annotated[CheckoutSelection, Query()],
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    addresses = list_addresses(db, user)
    if selection.shipping_address_id is None:
        default = next((a for a in addresses if a.is_default and a.type in SHIPPING_TYPES), None)
        if default is not None:
            selection = selection.model_copy(update={"shipping_address_id": default.id})
    quote = build_quote(db, user, selection)
    return CheckoutResponse(
        quote=quote_response(quote),
        addresses=[address_response(address) for address in addresses],
        payment_methods=[payment_method_response(method) for method in list_payment_methods(db, user)],
        fulfillment_options=options_for_quote(db, quote),
    )


@router.post("/checkout/validate", response_model=CheckoutQuote)
def validate_checkout(selection: CheckoutSelection, user: User = Depends(require_user), db: Session = Depends(get_db)):
    return quote_response(build_quote(db, user, selection))


@router.get("/fulfillment/options", response_model=list[FulfillmentOption])
def get_fulfillment_options(
    store_id: int,
    shipping_address_id: int | None = None,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    quote = build_quote(db, user, CheckoutSelection(store_id=store_id, shipping_address_id=shipping_address_id))
    return options_for_quote(db, quote)
