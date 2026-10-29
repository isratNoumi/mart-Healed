from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import require_user
from ..models import User
from ..schemas import OrderDetailResponse, OrderListResponse, PendingOrderResponse, PlaceOrderRequest
from ..services.order_service import create_pending_order, get_user_order, list_orders, order_detail, pending_order_response

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.post("", response_model=PendingOrderResponse, status_code=201)
def place_order(payload: PlaceOrderRequest, response: Response, user: User = Depends(require_user), db: Session = Depends(get_db)):
    order, created = create_pending_order(db, user, payload)
    if not created:
        response.status_code = 200
    return pending_order_response(db, order)


@router.get("", response_model=OrderListResponse)
def get_orders(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=50),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    return list_orders(db, user, page, limit)


@router.get("/{order_id}", response_model=OrderDetailResponse)
def get_order(order_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)):
    return order_detail(db, get_user_order(db, user, order_id))
