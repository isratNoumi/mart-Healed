from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import require_user
from ..models import User
from ..schemas import PaymentMethodRequest, PaymentMethodResponse
from ..services.payment_method_service import create_payment_method, list_payment_methods, payment_method_response

router = APIRouter(prefix="/api/payment-methods", tags=["payment methods"])


@router.get("", response_model=list[PaymentMethodResponse])
def get_payment_methods(user: User = Depends(require_user), db: Session = Depends(get_db)):
    return [payment_method_response(method) for method in list_payment_methods(db, user)]


@router.post("", response_model=PaymentMethodResponse, status_code=201)
def add_payment_method(payload: PaymentMethodRequest, user: User = Depends(require_user), db: Session = Depends(get_db)):
    method = create_payment_method(db, user, payload)
    db.commit()
    return payment_method_response(method)
