from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import require_user
from ..models import User
from ..schemas import CardInput, CardValidationResponse, PaymentDetailResponse, PaymentResult, ProcessPaymentRequest
from ..services.order_service import payment_detail, process_payment
from ..services.payment_service import check_card

router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.post("/validate", response_model=CardValidationResponse)
def validate_card(payload: CardInput, user: User = Depends(require_user)):
    check = check_card(payload.card_number.get_secret_value(), payload.expiry_month, payload.expiry_year, payload.cvv.get_secret_value())
    return CardValidationResponse(valid=check.valid, brand=check.brand, last4=check.last4, errors=check.errors)


@router.post("/process", response_model=PaymentResult)
def pay(payload: ProcessPaymentRequest, user: User = Depends(require_user), db: Session = Depends(get_db)):
    return process_payment(db, user, payload)


@router.get("/{transaction_id}", response_model=PaymentDetailResponse)
def get_payment(transaction_id: str, user: User = Depends(require_user), db: Session = Depends(get_db)):
    return payment_detail(db, user, transaction_id)
